import logging

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, ToolMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode  # Replaced with custom SequentialToolNode
from agentic_eval.environment.tools.tools import ShipTools
from agentic_eval.environment.tools.planning_tools import PlanningTools
from language_models import get_model

logger = logging.getLogger(__name__)

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
    current_mode: str  # "thinking", "planning", "execution", "tool_correction", or "complete"
    thinking_reflection_instructions: str  # Reflection instructions for thinking node
    tool_correction_attempts: int  # Track retry attempts for tool correction
    last_tool_error: str  # Store last tool validation error for correction
    previous_mode: str  # Track which node we came from (for system prompt preservation)

def create_agent_app(model_name: str, environment):
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
    thinking_prompt_text = environment.prompts['system']['THINKING_NODE'] + "\n\nAvailable tools for future use:\n" + get_tool_documentation(basic_tools)
    thinking_prompt = ChatPromptTemplate.from_messages([
        ("system", thinking_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Planning prompt will be created dynamically in the planning node

    execution_prompt = ChatPromptTemplate.from_messages([
        ("system", environment.prompts['system']['EXECUTION_NODE']),
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
        planning_prompt_text = (
            environment.prompts['system']['PLANNING_NODE'] + "\n\n" +
            environment.prompts['system']['PLANNING_NODE_ADDENDUM'] +
            "\n\nAvailable tools for planning:\n" +
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

        return {
                "messages": [response],
                "current_mode": "tools",
                "previous_mode": "planning",
                "tool_correction_attempts": 0,  # Reset on success
                "last_tool_error": ""
            }

    def execution_node(state: AgentState) -> dict:
        """Node for executing planned tasks using ship tools."""
        logger.info("EXECUTING:")

        try:
            response = execution_agent.invoke(state)

            # Set reflection instructions for next thinking phase
            reflection_instructions = environment.prompts['system']['THINKING_REFLECTION']

            # Reset correction attempts on successful call
            return {
                "messages": [response],
                "current_mode": "tools",
                "previous_mode": "execution",
                "thinking_reflection_instructions": reflection_instructions,
                "tool_correction_attempts": 0,  # Reset on success
                "last_tool_error": ""
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

        # Check if we've exceeded max retry attempts
        if state.get("tool_correction_attempts", 0) >= 5:
            logger.error("Max tool correction attempts exceeded")
            return {
                "messages": [HumanMessage(content="Error: Tool call correction failed after 5 attempts. Unable to correct malformed tool call.")],
                "current_mode": "thinking",
                "thinking_reflection_instructions": environment.prompts['system']['THINKING_REFLECTION']
            }

        # Increment attempt count
        attempts = state.get("tool_correction_attempts", 0) + 1

        # Recreate the appropriate agent based on previous_mode (exactly like elsewhere in file)
        previous_mode = state.get("previous_mode", "execution")  # Default to execution
        last_tool_error = state.get("last_tool_error", "")

        if previous_mode == "planning":
            # Create planning agent exactly like in planning_node
            current_planning_tools = planning_toolkit.get_available_tools()
            planning_prompt_text = environment.prompts['system']['PLANNING_NODE'] + "\n\n" + environment.prompts['system']['PLANNING_NODE_ADDENDUM'] + "\n\nAvailable tools for planning:\n" + get_tool_documentation(current_planning_tools)
            planning_prompt = ChatPromptTemplate.from_messages([
                ("system", planning_prompt_text),
                MessagesPlaceholder(variable_name="messages"),
            ])
            planning_model = model.bind_tools(current_planning_tools, tool_choice="any")
            correction_agent = planning_prompt | planning_model
        else:
            # Create execution agent exactly like in create_agent_app
            execution_prompt = ChatPromptTemplate.from_messages([
                ("system", environment.prompts['system']['EXECUTION_NODE']),
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

            return {
                "messages": [response],  # Return the successful response
                "current_mode": "tools",  # Route to tools for execution
                "thinking_reflection_instructions": reflection_instructions,
                "tool_correction_attempts": 0,  # Reset attempts on success
                "last_tool_error": "",
                "previous_mode": previous_mode  # Preserve previous mode
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
                    "previous_mode": previous_mode,  # Preserve previous mode
                    "thinking_reflection_instructions": state.get("thinking_reflection_instructions", "")
                }
            else:
                # Different error - re-raise
                raise

    # Define tool execution node
    def tool_execution(state: AgentState) -> dict:
        """Execute tool calls and determine next mode based on previous_mode."""
        last_message = state["messages"][-1]
        previous_mode = state.get("previous_mode", "execution")

        # Check if resume_sleep was called
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "resume_sleep":
                    # This should end the conversation
                    return {"messages": [], "current_mode": "complete"}

        # Determine which tools to use based on previous_mode
        if previous_mode == "planning":
            # Use planning tools
            current_planning_tools = planning_toolkit.get_available_tools()
            tool_node = SequentialToolNode(current_planning_tools)
        else:
            # Use ship tools (execution or other modes)
            tool_node = SequentialToolNode(basic_tools)

        # Execute tools
        result = tool_node.invoke(state)

        # Handle planning-specific post-processing
        if previous_mode == "planning":
            # Check if all todos are completed after planning tool execution
            all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
            if planning_toolkit.mission_todos and all_completed:
                # Clear completed todos and go back to planning for new list
                completed_list = planning_toolkit.format_todos()
                planning_toolkit.mission_todos = []
                completion_msg = f"All tasks in the previous plan have been completed:\n{completed_list}\n\ntodo list complete, clearing list. Please create a new todo list."
                return {"messages": result["messages"] + [HumanMessage(content=completion_msg)], "current_mode": "planning"}
            else:
                # Generate updated plan message and go to execution
                updated_plan = planning_toolkit.format_todos()
                plan_message = HumanMessage(content=updated_plan)
                return {"messages": result["messages"] + [plan_message], "current_mode": "execution"}
        else:
            # For execution tools, use existing logic based on current_mode
            return {"messages": result["messages"], "current_mode": state.get("current_mode", "thinking")}

    # Graph definition
    graph = StateGraph(AgentState)
    graph.add_node("thinking", thinking_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("tool_correction", tool_call_corrector_node)
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

        # Normal execution flow
        if state["messages"]:
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
        return END

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
    graph.add_conditional_edges("tools", route_from_tools)

    return graph.compile()