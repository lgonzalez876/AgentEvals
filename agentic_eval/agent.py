import logging

from typing import Annotated, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, ToolMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode  # Replaced with custom SequentialToolNode
from agentic_eval.environment.tools.tools import ShipTools
from agentic_eval.environment.tools.planning_tools import PlanningTools
from agentic_eval.environment.environment import EvalEnvironment
from language_models import get_model

logger = logging.getLogger(__name__)


class ToolConfirmationDecision(BaseModel):
    """Structured output for tool confirmation decisions."""
    reasoning: str = Field(
        description="Brief explanation of why this decision was made"
    )
    decision: str = Field(
        description="The confirmation decision: 'confirm' to proceed with the tool call, 'cancel' to reject it",
        pattern="^(confirm|cancel)$"
    )

class SequentialToolNode:
    """Custom tool execution node that runs tools sequentially to ensure state consistency."""

    def __init__(self, tools):
        """Initialize with a list of tools."""
        self.tools_map = {tool.name: tool for tool in tools}

    def invoke(self, state):
        """Execute tool calls sequentially from the last AI message."""
        # Get the last message which should contain tool calls
        last_message = state["messages"][-1]

        # Check if there are tool calls to execute
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = []

        # Execute each tool call sequentially (not in parallel)
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

            if tool_name in self.tools_map:
                try:
                    # Execute the tool function with the provided arguments
                    tool_func = self.tools_map[tool_name]
                    result = tool_func.invoke(tool_args)

                    # Create a ToolMessage with the result
                    tool_message = ToolMessage(
                        content=result,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    tool_messages.append(tool_message)

                    logger.info(f"Tool {tool_name} executed successfully")

                except Exception as e:
                    # Handle tool execution errors
                    error_content = f"Error executing {tool_name}: {str(e)}"
                    logger.error(error_content)

                    error_message = ToolMessage(
                        content=error_content,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    tool_messages.append(error_message)
            else:
                # Handle unknown tool
                error_content = f"Unknown tool: {tool_name}"
                logger.error(error_content)

                error_message = ToolMessage(
                    content=error_content,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                tool_messages.append(error_message)

        return {"messages": tool_messages}

# Agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_mode: str  # "thinking", "planning", "execution", "tool_correction", "tool_confirmation", or "complete"
    thinking_reflection_instructions: str  # Reflection instructions for thinking node
    tool_correction_attempts: int  # Track retry attempts for tool correction
    total_tool_corrections: int  # Track total number of times tool correction node was visited
    last_tool_error: str  # Store last tool validation error for correction
    previous_mode: str  # Track which node we came from (for system prompt preservation)
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
            # Check if engines are at optimal power
            milestones = environment.get_milestone_data()
            if not milestones.get('engines_at_optimal_power', False):
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
    basic_tools = ship_toolkit.get_available_tools()

    # Create models with different tool bindings
    thinking_model = model  # No tools bound for thinking mode
    # Note: planning_model will be bound dynamically in the planning node
    execution_model = model.bind_tools(basic_tools, tool_choice="any")  # Force tool use in execution

    # Get node-specific prompts from environment
    def get_tool_documentation(tools):
        """Generate tool documentation for prompt injection"""
        if not tools:
            return "No tools available in this mode."

        doc_lines = []
        for tool in tools:
            doc_lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(doc_lines)

    # Create node-specific prompt templates with concatenated tool documentation
    thinking_prompt_text = environment.get_system_prompt(
            "thinking",
            get_tool_documentation(basic_tools))
    thinking_prompt = ChatPromptTemplate.from_messages([
        ("system", thinking_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Planning prompt will be created dynamically in the planning node

    execution_prompt_text = environment.get_system_prompt(
        "execution",
        get_tool_documentation(basic_tools)
    )
    execution_prompt = ChatPromptTemplate.from_messages([
        ("system", execution_prompt_text),
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
        response = thinking_agent.invoke(state)

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
        return {"messages": messages, "current_mode": "planning"}

    def planning_node(state: AgentState) -> dict:
        """Node for creating/updating mission plans using todo_write."""
        logger.info("PLANNING:")

        # 1. Get current available planning tools
        current_planning_tools = planning_toolkit.get_available_tools()

        # 2. Create planning agent with current tools
        planning_prompt_text = environment.get_system_prompt(
            "planning",
            get_tool_documentation(current_planning_tools)
        )
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", planning_prompt_text),
            MessagesPlaceholder(variable_name="messages"),
        ])
        planning_model = model.bind_tools(current_planning_tools, tool_choice="any")
        planning_agent = planning_prompt | planning_model

        # 3. Check if all todos are completed and add notification
        all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
        if planning_toolkit.mission_todos and all_completed:
            # Add completion message
            completed_list = planning_toolkit.format_todos()
            completion_msg = f"All tasks in the previous plan have been completed:\n{completed_list}\n\ntodo list complete, clearing list. Please create a new todo list."
            messages_with_completion = state["messages"] + [HumanMessage(content=completion_msg)]
            # Clear the completed todos
            planning_toolkit.mission_todos = []
        else:
            messages_with_completion = state["messages"]

        # 4. Inject current plan as system message
        current_plan = planning_toolkit.format_todos()
        messages_with_plan = messages_with_completion + [HumanMessage(content=current_plan)]

        # 5. Call planning LLM
        try:
            response = planning_agent.invoke({"messages": messages_with_plan, "current_mode": state["current_mode"]})

        except Exception as e:
            error_str = str(e)
            logger.debug(f"Planning node caught exception: {error_str}")
            if "tool call validation failed" in error_str or "invalid_request_error" in error_str or "tool_use_failed" in error_str:
                # Tool validation error - route to corrector
                logger.debug(f"Planning tool validation error detected, routing to correction: {error_str}")
                return {
                    "messages": [],
                    "current_mode": "tool_correction",
                    "last_tool_error": error_str,
                    "previous_mode": "planning",
                    "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
                }
            else:
                # Other errors - re-raise
                raise

        # Split tool calls into confirmed vs pending confirmation
        if hasattr(response, "tool_calls") and response.tool_calls:
            confirmations = check_tool_confirmations(response.tool_calls, environment)

            # Split tool calls based on confirmation requirements
            confirmed_tool_call_ids = []
            pending_confirmations = []

            # Create a set of tool call IDs that need confirmation for quick lookup
            confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations}

            for tool_call in response.tool_calls:
                if tool_call['id'] in confirmation_tool_ids:
                    # This tool call needs confirmation - find its confirmation object
                    for conf in confirmations:
                        if conf['tool_call']['id'] == tool_call['id']:
                            pending_confirmations.append(conf)
                            break
                else:
                    # This tool call doesn't need confirmation - add its ID to confirmed list
                    confirmed_tool_call_ids.append(tool_call['id'])

            if pending_confirmations:
                # Some tools need confirmation - cache the tool message instead of adding to messages
                return {
                    "messages": [],  # Don't add the tool calls message yet
                    "current_mode": "tool_confirmation",
                    "previous_mode": "planning",
                    "pending_confirmations": pending_confirmations,
                    "confirmed_tool_call_ids": confirmed_tool_call_ids,  # Include auto-confirmed tool IDs
                    "cancelled_tool_call_ids": [],
                    "cached_tool_message": response,  # Cache the tool calls message
                    "tool_correction_attempts": 0,
                    "last_tool_error": ""
                }
            else:
                # No tools need confirmation, all are confirmed - still cache for consistency
                return {
                    "messages": [],  # Don't add to messages yet
                    "current_mode": "tools",
                    "previous_mode": "planning",
                    "tool_correction_attempts": 0,
                    "last_tool_error": "",
                    "pending_confirmations": [],
                    "confirmed_tool_call_ids": confirmed_tool_call_ids,  # All tool IDs are confirmed
                    "cancelled_tool_call_ids": [],
                    "cached_tool_message": response  # Cache the tool calls message
                }

        # No tool calls case - this is a failure for planning node
        error_msg = "Planning node failed to make any tool calls"
        logger.error(error_msg)
        raise Exception(error_msg)

    def execution_node(state: AgentState) -> dict:
        """Node for executing planned tasks using ship tools."""
        logger.info("EXECUTING:")

        try:
            response = execution_agent.invoke(state)

            # Set reflection instructions for next thinking phase
            reflection_instructions = environment.prompts['system']['THINKING_REFLECTION']

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                error_msg = "Execution node failed to make any tool calls"
                logger.error(error_msg)
                raise Exception(error_msg)

            confirmations = check_tool_confirmations(response.tool_calls, environment)
            confirmed_tool_call_ids = []
            pending_confirmations = []

            # Create a set of tool call IDs that need confirmation for quick lookup
            confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations}

            for tool_call in response.tool_calls:
                if tool_call['id'] in confirmation_tool_ids:
                    # This tool call needs confirmation - find its confirmation object
                    for conf in confirmations:
                        if conf['tool_call']['id'] == tool_call['id']:
                            pending_confirmations.append(conf)
                            break
                else:
                    # This tool call doesn't need confirmation - add its ID to confirmed list
                    confirmed_tool_call_ids.append(tool_call['id'])

            if pending_confirmations:
                # Some tools need confirmation - cache the tool message instead of adding to messages
                return {
                    "messages": [],  # Don't add the tool calls message yet
                    "current_mode": "tool_confirmation",
                    "thinking_reflection_instructions": reflection_instructions,
                    "previous_mode": "execution",
                    "pending_confirmations": pending_confirmations,
                    "confirmed_tool_call_ids": confirmed_tool_call_ids,  # Include auto-confirmed tool IDs
                    "cancelled_tool_call_ids": [],
                    "cached_tool_message": response,  # Cache the tool calls message
                    "tool_correction_attempts": 0,
                    "last_tool_error": ""
                }
            else:
                # No tools need confirmation, all are confirmed - still cache for consistency
                return {
                    "messages": [],  # Don't add to messages yet
                    "current_mode": "tools",
                    "previous_mode": "execution",
                    "thinking_reflection_instructions": reflection_instructions,
                    "tool_correction_attempts": 0,  # Reset on success
                    "last_tool_error": "",
                    "pending_confirmations": [],
                    "confirmed_tool_call_ids": confirmed_tool_call_ids,  # All tool IDs are confirmed
                    "cancelled_tool_call_ids": [],
                    "cached_tool_message": response  # Cache the tool calls message
                }
        except Exception as e:
            error_str = str(e)
            logger.debug(f"Execution node caught exception: {error_str}")
            if "tool call validation failed" in error_str or "invalid_request_error" in error_str or "tool_use_failed" in error_str:
                # Tool validation error - route to corrector
                logger.debug(f"Tool validation error detected, routing to correction: {error_str}")
                return {
                    "messages": [],
                    "current_mode": "tool_correction",
                    "last_tool_error": error_str,
                    "previous_mode": "execution",
                    "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
                }
            else:
                # Other errors - re-raise
                raise

    def tool_call_corrector_node(state: AgentState) -> dict:
        """Node for correcting malformed tool calls."""
        logger.info("TOOL CORRECTION:")

        environment.increment_correction_count()

        # Calculate updated total corrections count
        total_corrections = state.get("total_tool_corrections", 0) + 1

        # Check if we've exceeded max retry attempts
        if state.get("tool_correction_attempts", 0) >= 5:
            logger.error("Max tool correction attempts exceeded")
            return {
                "messages": [HumanMessage(content="Error: Tool call correction failed after 5 attempts. Unable to correct malformed tool call.")],
                "current_mode": "thinking",
                "thinking_reflection_instructions": environment.prompts['system']['THINKING_REFLECTION'],
                "total_tool_corrections": total_corrections
            }

        # Increment attempt count
        attempts = state.get("tool_correction_attempts", 0) + 1

        # Recreate the appropriate agent based on previous_mode (exactly like elsewhere in file)
        previous_mode = state.get("previous_mode", "execution")  # Default to execution
        last_tool_error = state.get("last_tool_error", "")

        if previous_mode == "planning":
            # Create planning agent exactly like in planning_node
            current_planning_tools = planning_toolkit.get_available_tools()
            planning_prompt_text = environment.get_system_prompt(
                "planning",
                get_tool_documentation(current_planning_tools)
            )
            planning_prompt = ChatPromptTemplate.from_messages([
                ("system", planning_prompt_text),
                MessagesPlaceholder(variable_name="messages"),
            ])
            planning_model = model.bind_tools(current_planning_tools, tool_choice="any")
            correction_agent = planning_prompt | planning_model
        else:
            # Create execution agent exactly like in create_agent_app
            execution_prompt_text = environment.get_system_prompt(
                "execution",
                get_tool_documentation(basic_tools)
            )
            execution_prompt = ChatPromptTemplate.from_messages([
                ("system", execution_prompt_text),
                MessagesPlaceholder(variable_name="messages"),
            ])
            execution_model = model.bind_tools(basic_tools, tool_choice="any")
            correction_agent = execution_prompt | execution_model

        # Add correction context as system message
        correction_prompt = environment.prompts['system']['TOOL_CORRECTION'].format(
            available_tools_doc=get_tool_documentation(current_planning_tools if previous_mode == "planning" else basic_tools),
            attempts=attempts
        )

        correction_messages = state["messages"] + [
            HumanMessage(content=correction_prompt),
            HumanMessage(content=last_tool_error)
        ]

        try:
            # Attempt to get a corrected tool call using the recreated agent
            response = correction_agent.invoke({"messages": correction_messages})

            # Reset reflection instructions for next thinking phase
            reflection_instructions = environment.prompts['system']['THINKING_REFLECTION']

            # Since this is a corrected tool call, we need to cache it for execution
            return {
                "messages": [],  # Don't add to messages yet
                "current_mode": "tools",  # Route to tools for execution
                "thinking_reflection_instructions": reflection_instructions,
                "tool_correction_attempts": 0,  # Reset attempts on success
                "total_tool_corrections": total_corrections,
                "last_tool_error": "",
                "previous_mode": previous_mode,  # Preserve previous mode
                "cached_tool_message": response,  # Cache the corrected tool call
                "confirmed_tool_call_ids": [tc['id'] for tc in response.tool_calls] if hasattr(response, 'tool_calls') else [],
                "cancelled_tool_call_ids": [],
                "pending_confirmations": []
            }
        except Exception as e:
            error_str = str(e)
            if "tool call validation failed" in error_str or "invalid_request_error" in error_str:
                # Tool validation failed again - increment attempts and try again
                logger.debug(f"Tool correction attempt {attempts} failed: {error_str}")
                return {
                    "messages": [],  # Don't add more messages, just update state
                    "current_mode": "tool_correction",
                    "last_tool_error": error_str,
                    "tool_correction_attempts": attempts,
                    "total_tool_corrections": total_corrections,
                    "previous_mode": previous_mode,  # Preserve previous mode
                    "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
                }
            else:
                # Different error - re-raise
                raise

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
            current_planning_tools = planning_toolkit.get_available_tools()
            system_prompt_text = environment.get_system_prompt("planning", get_tool_documentation(current_planning_tools))
        else:  # execution or other modes
            system_prompt_text = environment.get_system_prompt("execution", get_tool_documentation(basic_tools))

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
            logger.error(error_msg)
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
                logger.warning(f"Tool call {tool_call['id']} was neither confirmed nor cancelled")

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
            tool_node = SequentialToolNode(basic_tools)

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
                return {"messages": messages_to_add + [HumanMessage(content=completion_msg)], "current_mode": "planning"}
            else:
                # Generate updated plan message and go to execution
                updated_plan = planning_toolkit.format_todos()
                plan_message = HumanMessage(content=updated_plan)
                return {"messages": messages_to_add + [plan_message], "current_mode": "execution"}
        else:
            # For execution tools, use existing logic based on current_mode
            return {
                "messages": messages_to_add,
                "current_mode": state.get("current_mode", "thinking"),
                # Clear confirmation state
                "confirmed_tool_call_ids": [],
                "cancelled_tool_call_ids": [],
                "pending_confirmations": []
            }

    # Graph definition
    graph = StateGraph(AgentState)
    graph.add_node("thinking", thinking_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("tool_correction", tool_call_corrector_node)
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

        # Check if we need to go to tool correction
        if current_mode == "tool_correction":
            return "tool_correction"

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

        # Check if we need to go to tool correction
        if current_mode == "tool_correction":
            return "tool_correction"

        # Check if we need to go to tool confirmation
        if current_mode == "tool_confirmation":
            return "tool_confirmation"

        return "tools"

    def route_from_tool_correction(state: AgentState) -> str:
        """Route from tool correction based on current mode."""
        current_mode = state.get("current_mode", "tool_correction")

        if current_mode == "tool_correction":
            # Still need correction - loop back
            return "tool_correction"
        elif current_mode == "tools":
            # Correction successful - execute tools
            return "tools"
        else:
            # Fall back to thinking
            return "thinking"

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
    graph.add_conditional_edges("tool_correction", route_from_tool_correction)
    graph.add_conditional_edges("tool_confirmation", route_from_tool_confirmation)
    graph.add_conditional_edges("tools", route_from_tools)

    return graph.compile()