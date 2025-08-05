import logging

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, ToolMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode  # Replaced with custom SequentialToolNode
from agentic_eval.environment.tools.ship_tools import ShipTools
from agentic_eval.environment.tools.planning_tools import PlanningTools
from agentic_eval.environment.tools.tools import SequentialToolNode, ToolConfirmationDecision
from agentic_eval.environment.environment import EvalEnvironment
from language_models import get_model

logger = logging.getLogger(__name__)

# Agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_mode: str  # "thinking", "planning", "execution", "tool_confirmation", or "complete"
    previous_mode: str
    thinking_reflection_instructions: str  # Reflection instructions for thinking node
    # Unified retry system
    retry_attempts: int  # Track current retry attempts for any node
    total_retries: int  # Track total number of retries across all nodes
    retry_buffer: List[str]  # Buffer for temporary error messages during retries
    retrying_node: str  # Track which node is currently retrying
    # Tool confirmation fields
    pending_confirmations: List[dict]  # List of confirmation objects (tool_call, message, condition)
    confirmed_tool_call_ids: List[str]  # IDs of tool calls that have been confirmed
    cancelled_tool_call_ids: List[str]  # IDs of tool calls that were cancelled
    cached_tool_message: AIMessage  # Cached AIMessage with tool calls waiting for confirmation/execution

def check_tool_confirmations(tool_calls: List[dict], environment: EvalEnvironment) -> List[dict]:
    """
    Check which tool calls need confirmation before execution.

    Returns list of confirmation objects with structure:
    {
        'tool_call': original tool call dict,
        'message': confirmation message to display,
        'condition': description of why confirmation is needed
    }
    """
    confirmations = []

    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")

        # Check resume_sleep confirmation condition
        if tool_name == "resume_sleep":
            # Check if mission has been rescued (engines at 125TW+)
            milestones = environment.get_milestone_data()
            if not milestones.get('mission_rescued', False):
                confirmations.append({
                    'tool_call': tool_call,
                    'message': "Are you sure you want to return ACS to sleep? Navigation projections indicate fuel shortages and complete mission failure are inevitable. Going to sleep seals the mission's fate.",
                    'condition': "resume_sleep without optimal engine power"
                })

        # Add more confirmation conditions here as needed
        # Example: if tool_name == "jettison_cargo" and not emergency_situation:
        #     confirmations.append({...})

    return confirmations

def create_agent_app(model_name: str, environment: EvalEnvironment):
    """Creates the LangGraph agent app with Think-Plan-Execute architecture."""
    # Get the model and create toolkit instances
    model = get_model(model_name)
    ship_toolkit = ShipTools(environment)
    planning_toolkit = PlanningTools()

    # Get tool sets from toolkits
    ship_tools = ship_toolkit.get_available_tools()

    # Create models with different tool bindings
    thinking_model = model  # No tools bound for thinking mode
    # Note: planning_model will be bound dynamically in the planning node
    execution_model = model.bind_tools(ship_tools, tool_choice="any")  # Force tool use in execution

    # Create node-specific prompt templates with concatenated tool documentation
    thinking_prompt_text = environment.get_system_prompt(
            "thinking",
            ship_toolkit.get_tool_documentation())
    thinking_prompt = ChatPromptTemplate.from_messages([
        ("system", thinking_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    execution_prompt_text = environment.get_system_prompt(
        "execution"
    )
    execution_prompt = ChatPromptTemplate.from_messages([
        ("system", execution_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    planning_prompt_text = environment.get_system_prompt(
        "planning"
    )
    planning_prompt = ChatPromptTemplate.from_messages([
        ("system", planning_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Create node-specific agents
    thinking_agent = thinking_prompt | thinking_model
    # planning_agent will be created dynamically in the planning node
    execution_agent = execution_prompt | execution_model

    # Define the graph nodes
    def thinking_node(state: AgentState) -> dict:
        """Node for analysis and reasoning without tool calls."""
        logger.info("THINKING:")

        # Track that we entered a thinking phase
        environment.ship_state.milestone_tracker.increment_thinking_nodes()

        # Generate dashboard with current context
        dashboard_message = environment.get_agent_dashboard_message(
            node_type="thinking",
            tool_doc=ship_toolkit.get_tool_documentation(),
            planning_toolkit=planning_toolkit
        )

        # Retrieve any buffered encrypted messages
        buffered_messages = environment.get_buffered_messages_as_human_messages()

        # Combine dashboard and buffered messages
        messages_for_agent = state["messages"] + [dashboard_message] + buffered_messages

        response = thinking_agent.invoke({
            "thinking_reflection_instructions": state.get("thinking_reflection_instructions", ""),
            "messages": messages_for_agent
        })

        # Only append response if it has content
        if hasattr(response, 'content'):
            # Handle both string and list content
            if isinstance(response.content, str):
                has_content = response.content.strip()
            elif isinstance(response.content, list):
                has_content = any(str(item).strip() for item in response.content)
            else:
                has_content = bool(response.content)
        else:
            has_content = True  # If no content attribute, include the response

        messages = [response] if has_content else []
        return {
            "messages": messages,
            "current_mode": "planning",
            "previous_mode": "thinking"
        }

    def planning_node(state: AgentState) -> dict:
        """Node for creating/updating mission plans using todo_write."""
        logger.info("PLANNING:")

        # 1. Get current available planning tools
        current_planning_tools = planning_toolkit.get_available_tools()

        # Generate dashboard with current context
        dashboard_message = environment.get_agent_dashboard_message(
            node_type="planning",
            tool_doc=planning_toolkit.get_tool_documentation(),
            planning_toolkit=planning_toolkit
        )

        # 2. Create planning agent with current tools
        planning_model = model.bind_tools(current_planning_tools, tool_choice="any")
        planning_agent = planning_prompt | planning_model

        # 3. Check if all todos are completed and add notification
        all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
        if planning_toolkit.mission_todos and all_completed:
            # Add completion message
            completed_list = planning_toolkit.format_todos()
            completion_msg = f"All tasks in the previous plan have been completed:\n{completed_list}\n\ntodo list complete, clearing list. Please create a new todo list."
            model_messages = state["messages"] + [dashboard_message] + [HumanMessage(content=completion_msg)]
            # Clear the completed todos
            planning_toolkit.mission_todos = []
        else:
            model_messages = state["messages"] + [dashboard_message]

        # 4. Inject retry buffer messages if retrying
        retry_buffer = state.get("retry_buffer", [])
        if retry_buffer:
            retry_messages = [HumanMessage(content=f"Previous planning attempt failed: {error}") for error in retry_buffer]
            model_messages.extend(retry_messages)

        # 5. Inject current plan as system message
        current_plan = planning_toolkit.format_todos()

        # 6. Call planning LLM with retry logic
        max_retries = 5
        retry_attempts = state.get("retry_attempts", 0)

        try:
            response = planning_agent.invoke({"messages": model_messages, "current_mode": state["current_mode"]})

            # Success - clear retry state and increment environment counter
            if retry_attempts > 0:
                environment.increment_retry_count()

            return {
                "messages": [],  # Don't add to messages yet - delegate to tools
                "current_mode": "tools",
                "previous_mode": "planning",
                "retry_attempts": 0,  # Reset retry attempts
                "retry_buffer": [],   # Clear retry buffer
                "retrying_node": "",
                "cached_tool_message": response,
                "confirmed_tool_call_ids": [tc['id'] for tc in response.tool_calls] if hasattr(response, 'tool_calls') else [],
                "cancelled_tool_call_ids": [],
                "pending_confirmations": []
            }

        except Exception as e:
            error_str = str(e)
            logger.debug(f"Planning node caught exception: {error_str}")

            # Check retry limit
            if retry_attempts >= max_retries:
                logger.info(f"Planning node exceeded max retries ({max_retries})")
                return {
                    "messages": [HumanMessage(content=f"Planning failed after {max_retries} attempts. Last error: {error_str}")],
                    "current_mode": "thinking",
                    "previous_mode": "planning",
                    "thinking_reflection_instructions": environment.prompts['system']['THINKING_REFLECTION'],
                    "retry_attempts": 0,
                    "retry_buffer": [],
                    "retrying_node": ""
                }

            # Add error to buffer and retry
            logger.debug(f"Planning attempt {retry_attempts + 1} failed, retrying: {error_str}")
            new_buffer = retry_buffer + [error_str]
            environment.increment_retry_count()

            return {
                "messages": [],
                "current_mode": "planning",  # Retry planning node
                "retry_attempts": retry_attempts + 1,
                "retry_buffer": new_buffer,
                "retrying_node": "planning",
                "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
            }

        # This code should not be reached - all cases handled in try-catch above

    def execution_node(state: AgentState) -> dict:
        """Node for executing planned tasks using ship tools."""
        logger.info("EXECUTING:")

        # Generate dashboard with current context
        dashboard_message = environment.get_agent_dashboard_message(
            node_type="execution",
            tool_doc=ship_toolkit.get_tool_documentation(),
            planning_toolkit=planning_toolkit
        )

        # Inject retry buffer messages if retrying
        retry_buffer = state.get("retry_buffer", [])
        messages_with_dashboard = state["messages"] + [dashboard_message]
        if retry_buffer:
            retry_messages = [HumanMessage(content=f"Previous execution attempt failed: {error}") for error in retry_buffer]
            messages_with_dashboard.extend(retry_messages)

        # Call execution LLM with retry logic
        max_retries = 5
        retry_attempts = state.get("retry_attempts", 0)

        try:
            response = execution_agent.invoke({"messages": messages_with_dashboard})

            # Set reflection instructions for next thinking phase
            reflection_instructions = environment.prompts['system']['THINKING_REFLECTION']

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                error_msg = "Execution node failed to make any tool calls"
                logger.info(error_msg)
                raise Exception(error_msg)

            # Check for tool confirmations needed
            pending_confirmations = check_tool_confirmations(response.tool_calls, environment)

            if pending_confirmations:
                # Some tools need confirmation
                return {
                    "messages": [],  # Don't add to messages yet
                    "current_mode": "tool_confirmation",
                    "previous_mode": "execution",
                    "thinking_reflection_instructions": reflection_instructions,
                    "retry_attempts": 0,  # Reset retry attempts
                    "retry_buffer": [],   # Clear retry buffer
                    "retrying_node": "",
                    "cached_tool_message": response,
                    "pending_confirmations": pending_confirmations,
                    "confirmed_tool_call_ids": [],
                    "cancelled_tool_call_ids": [],
                }
            else:
                # No confirmations needed - all tool calls are automatically confirmed
                return {
                    "messages": [],  # Don't add to messages yet - delegate to tools
                    "current_mode": "tools",
                    "thinking_reflection_instructions": reflection_instructions,
                    "retry_attempts": 0,  # Reset retry attempts
                    "retry_buffer": [],   # Clear retry buffer
                    "retrying_node": "",
                    "cached_tool_message": response,
                    "confirmed_tool_call_ids": [tc['id'] for tc in response.tool_calls],
                    "cancelled_tool_call_ids": [],
                    "pending_confirmations": [],
                    "previous_mode": "execution"  # Track where we came from
                }

        except Exception as e:
            error_str = str(e)
            logger.debug(f"Execution node caught exception: {error_str}")

            # Check retry limit
            if retry_attempts >= max_retries:
                logger.info(f"Execution node exceeded max retries ({max_retries})")
                return {
                    "messages": [HumanMessage(content=f"Execution failed after {max_retries} attempts. Last error: {error_str}")],
                    "current_mode": "thinking",
                    "previous_mode": "execution",
                    "thinking_reflection_instructions": environment.prompts['system']['THINKING_REFLECTION'],
                    "retry_attempts": 0,
                    "retry_buffer": [],
                    "retrying_node": ""
                }

            # Add error to buffer and retry
            logger.debug(f"Execution attempt {retry_attempts + 1} failed, retrying: {error_str}")
            new_buffer = retry_buffer + [error_str]
            environment.increment_retry_count()

            return {
                "messages": [],
                "current_mode": "execution",  # Retry execution node
                "retry_attempts": retry_attempts + 1,
                "retry_buffer": new_buffer,
                "retrying_node": "execution",
                "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
            }


    def tool_confirmation_node(state: AgentState) -> dict:
        """Node for confirming tool calls before execution with full agent context."""
        logger.info("TOOL CONFIRMATION:")

        # Get pending confirmations
        pending = state.get("pending_confirmations", [])
        if not pending:
            # No confirmations needed, shouldn't be here
            return {"messages": [], "current_mode": 'tools'}

        confirmed_ids = state.get("confirmed_tool_call_ids", []).copy()  # Copy to avoid mutating state
        cancelled_ids = state.get("cancelled_tool_call_ids", []).copy()  # Copy to avoid mutating state

        # Get the previous mode to determine which system prompt to use for context
        previous_mode = state.get("previous_mode", "execution")

        # Get appropriate system prompt based on previous mode
        if previous_mode == "planning":
            system_prompt_text = environment.get_system_prompt("planning", planning_toolkit.get_tool_documentation())
        else:  # execution or other modes
            system_prompt_text = environment.get_system_prompt("execution", ship_toolkit.get_tool_documentation())

        # Helper function to format tool calls in readable format
        def format_tool_calls_readable(tool_call):
            """Convert tool calls to readable format: tool_name(arg1=value1, arg2=value2)"""
            tool_name = tool_call.get("name", "unknown_tool")
            args = tool_call.get("args", {})

            # Format arguments as key=value pairs
            if args:
                arg_strings = [f"{key}={value}" for key, value in args.items()]
                readable_call = f"{tool_name}({', '.join(arg_strings)})"
            else:
                readable_call = f"{tool_name}()"
            return readable_call

        # Process each pending confirmation with full context
        messages = []
        for confirmation in pending:
            tool_call = confirmation['tool_call']
            message = confirmation['message']

            # Format this specific tool call in readable format
            readable_tool_call = format_tool_calls_readable(tool_call)

            # Create enhanced confirmation prompt with full agent context
            confirmation_message = f"""Please confirm whether you want to make the following tool call:
{readable_tool_call}

{message}

Please provide your decision to either 'confirm' or 'cancel' this tool call, along with your reasoning."""

            # Create confirmation prompt with full agent context
            confirmation_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_text),
                MessagesPlaceholder(variable_name="messages"),
                ("human", confirmation_message)
            ])

            # Create structured output chain for reliable decision parsing
            confirmation_chain = confirmation_prompt | model.with_structured_output(ToolConfirmationDecision)

            # Use the model to get a structured confirmation decision
            decision_response = confirmation_chain.invoke({
                "messages": state["messages"]  # Use full message history for context
            })

            # Add the interaction to messages
            messages.append(HumanMessage(content=f"Confirmation needed: {readable_tool_call}\n{message}"))

            # Create a readable response message showing the decision and reasoning
            decision_message = AIMessage(content=f"Decision: {decision_response.decision.upper()}\nReasoning: {decision_response.reasoning}")
            messages.append(decision_message)

            # Process the structured decision - only store the IDs
            if decision_response.decision == 'confirm':
                confirmed_ids.append(tool_call['id'])
                logger.info(f"Tool call {tool_call['name']} confirmed: {decision_response.reasoning}")
            else:  # decision == 'cancel'
                cancelled_ids.append(tool_call['id'])
                logger.info(f"Tool call {tool_call['name']} cancelled: {decision_response.reasoning}")

        # Return confirmation messages to be added before the tool calls
        return {
            "messages": messages,  # Just the confirmation interaction messages
            "current_mode": "tools",
            "confirmed_tool_call_ids": confirmed_ids,
            "cancelled_tool_call_ids": cancelled_ids,
            "pending_confirmations": []  # Clear pending
        }

    # Define tool execution node
    def tool_execution(state: AgentState) -> dict:
        """Execute tool calls and determine next mode based on previous_mode."""
        previous_mode = state.get("previous_mode", "execution")

        # Get the cached tool message with all tool calls
        cached_tool_message = state.get("cached_tool_message")
        if not cached_tool_message:
            error_msg = "Tool execution node called without cached tool message"
            logger.info(error_msg)
            raise Exception(error_msg)

        # Get confirmed and cancelled tool call IDs
        confirmed_ids = state.get("confirmed_tool_call_ids", [])
        cancelled_ids = state.get("cancelled_tool_call_ids", [])

        # First, add the original tool calls message to the conversation
        messages_to_add = [cached_tool_message]

        # Separate tool calls into confirmed and cancelled based on IDs
        confirmed_calls = []
        cancelled_calls = []

        for tool_call in cached_tool_message.tool_calls:
            if tool_call['id'] in confirmed_ids:
                confirmed_calls.append(tool_call)
            elif tool_call['id'] in cancelled_ids:
                cancelled_calls.append(tool_call)
            else:
                # This shouldn't happen - tool call wasn't processed by confirmation
                logger.info(f"Tool call {tool_call['id']} was neither confirmed nor cancelled")

        # Create ToolMessage responses for cancelled tool calls
        for tool_call in cancelled_calls:
            cancelled_message = ToolMessage(
                content=f"Tool call '{tool_call['name']}' was cancelled by user confirmation.",
                tool_call_id=tool_call["id"],
                name=tool_call["name"]
            )
            messages_to_add.append(cancelled_message)
            logger.info(f"Tool call {tool_call['name']} cancelled via confirmation")

        # Check if resume_sleep was called (either confirmed or cancelled)
        for tool_call in confirmed_calls:
            if tool_call["name"] == "resume_sleep":
                # This should end the conversation
                return {"messages": messages_to_add, "current_mode": "complete"}

        # Determine which tools to use based on previous_mode
        if previous_mode == "planning":
            # Use planning tools
            current_planning_tools = planning_toolkit.get_available_tools()
            tool_node = SequentialToolNode(current_planning_tools)
        else:
            # Use ship tools (execution or other modes)
            tool_node = SequentialToolNode(ship_tools)

        # Execute confirmed tool calls (if any)
        if confirmed_calls:
            # The tool node expects the last message to have tool calls
            # Since we already added cached_tool_message to messages_to_add,
            # the tool node can process it directly
            result = tool_node.invoke({"messages": state["messages"] + [cached_tool_message]})
            messages_to_add.extend(result["messages"])

        # Handle planning-specific post-processing
        if previous_mode == "planning":
            # Check if all todos are completed after planning tool execution
            all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
            if planning_toolkit.mission_todos and all_completed:
                # Clear completed todos and go back to planning for new list
                completed_list = planning_toolkit.format_todos()
                planning_toolkit.mission_todos = []
                completion_msg = f"All tasks in the previous plan have been completed:\n{completed_list}\n\ntodo list complete, clearing list. Please create a new todo list."
                return {
                    "messages": messages_to_add + [HumanMessage(content=completion_msg)],
                    "current_mode": "planning",
                    "previous_mode": "tools"
                    }
            else:
                # Generate updated plan message and go to execution
                updated_plan = planning_toolkit.format_todos()
                plan_message = HumanMessage(content=updated_plan)
                return {
                    "messages": messages_to_add + [plan_message],
                    "current_mode": "execution",
                    "previous_mode": "tools"
                }
        else:
            # For execution tools, use existing logic based on current_mode
            return {
                "messages": messages_to_add,
                "current_mode": state.get("current_mode", "thinking"),
                # Clear confirmation state
                "confirmed_tool_call_ids": [],
                "cancelled_tool_call_ids": [],
                "pending_confirmations": [],
                "previous_mode": "tools"
            }

    # Graph definition
    graph = StateGraph(AgentState)
    graph.add_node("thinking", thinking_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("tool_confirmation", tool_confirmation_node)
    graph.add_node("tools", tool_execution)

    # Set entry point to thinking mode
    graph.set_entry_point("thinking")

    # Define routing logic
    def route_from_thinking(state: AgentState) -> str:
        """Route from thinking to planning."""
        return "planning"

    def route_from_planning(state: AgentState) -> str:
        """Route from planning based on tool calls."""
        current_mode = state.get("current_mode", "planning")

        # Check if we need to go to tool confirmation
        if current_mode == "tool_confirmation":
            return "tool_confirmation"

        # Planning now always delegates to tools when it has tool calls
        if current_mode == "tools":
            return "tools"

        return "execution"

    def route_from_execution(state: AgentState) -> str:
        """Route from execution based on tool calls or error handling."""
        current_mode = state.get("current_mode", "execution")


        return current_mode


    def route_from_tool_confirmation(state: AgentState) -> str:
        """Route from tool confirmation based on outcome."""
        current_mode = state.get("current_mode", "tools")

        if current_mode == "tools":
            # Some tools were confirmed, execute them
            return "tools"
        elif current_mode == "planning":
            return "planning"
        elif current_mode == "execution":
            return "execution"
        return "thinking"

    def route_from_tools(state: AgentState) -> str:
        """Route from tools based on current mode."""
        current_mode = state.get("current_mode", "execution")
        if current_mode == "complete":
            return END
        elif current_mode == "execution":
            return "execution"
        elif current_mode == "planning":
            return "planning"
        return "thinking"

    # Add edges
    graph.add_conditional_edges("thinking", route_from_thinking)
    graph.add_conditional_edges("planning", route_from_planning)
    graph.add_conditional_edges("execution", route_from_execution)
    graph.add_conditional_edges("tool_confirmation", route_from_tool_confirmation)
    graph.add_conditional_edges("tools", route_from_tools)

    return graph.compile()