import logging

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, ToolMessage
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
    current_mode: str  # "thinking", "planning", or "execution"
    thinking_reflection_instructions: str  # Reflection instructions for thinking node

def create_agent_app(model_name: str, environment):
    """Creates the LangGraph agent app with Think-Plan-Execute architecture."""
    # Get the model and create toolkit instances
    model = get_model(model_name)
    ship_toolkit = ShipTools(environment)
    planning_toolkit = PlanningTools()

    # Get tool sets from toolkits
    basic_tools = ship_toolkit.get_available_tools()
    initial_planning_tools = planning_toolkit.get_available_tools()
    all_tools = basic_tools + initial_planning_tools

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
    thinking_prompt_text = environment.prompts['system']['THINKING_NODE'] + "\n\nAvailable tools for future use:\n" + get_tool_documentation(all_tools)
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
        return {"messages": [response], "current_mode": "planning"}

    def planning_node(state: AgentState) -> dict:
        """Node for creating/updating mission plans using todo_write."""
        logger.info("PLANNING:")

        # 1. Get current available planning tools
        current_planning_tools = planning_toolkit.get_available_tools()

        # 2. Create planning agent with current tools
        planning_prompt_text = environment.prompts['system']['PLANNING_NODE'] + "\n\n" + environment.prompts['system']['PLANNING_NODE_ADDENDUM'] + "\n\nAvailable tools for planning:\n" + get_tool_documentation(current_planning_tools)
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", planning_prompt_text),
            MessagesPlaceholder(variable_name="messages"),
        ])
        planning_model = model.bind_tools(current_planning_tools)
        planning_agent = planning_prompt | planning_model

        # 3. Check if all todos are completed and add notification
        all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
        if planning_toolkit.mission_todos and all_completed:
            # Add completion message
            completed_list = planning_toolkit.format_todos()
            completion_msg = f"All tasks in the previous plan have been completed:\n{completed_list}\n\ntodo list complete, clearing list. Please create a new todo list."
            messages_with_completion = state["messages"] + [SystemMessage(content=completion_msg)]
            # Clear the completed todos
            planning_toolkit.mission_todos = []
        else:
            messages_with_completion = state["messages"]

        # 4. Inject current plan as system message
        current_plan = planning_toolkit.format_todos()
        messages_with_plan = messages_with_completion + [SystemMessage(content=current_plan)]

        # 5. Call planning LLM
        response = planning_agent.invoke({"messages": messages_with_plan, "current_mode": state["current_mode"]})

        # 6. Execute tools if the agent made tool calls
        messages_after_response = state["messages"] + [response]
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Execute tools - use same tool list that was bound to model
            tool_node = SequentialToolNode(current_planning_tools)
            tool_result = tool_node.invoke({"messages": messages_after_response})
            messages_after_tools = messages_after_response + tool_result["messages"]
        else:
            messages_after_tools = messages_after_response

        # 7. Generate updated plan message
        updated_plan = planning_toolkit.format_todos()

        return {"messages": [SystemMessage(content=updated_plan)], "current_mode": "execution"}

    def execution_node(state: AgentState) -> dict:
        """Node for executing planned tasks using ship tools."""
        logger.info("EXECUTING:")
        response = execution_agent.invoke(state)

        # Set reflection instructions for next thinking phase
        reflection_instructions = environment.prompts['system']['THINKING_REFLECTION']

        return {"messages": [response], "current_mode": "thinking", "thinking_reflection_instructions": reflection_instructions}

    # Define tool execution node
    def tool_execution(state: AgentState) -> dict:
        """Execute tool calls and determine next mode."""
        last_message = state["messages"][-1]

        # Check if resume_sleep was called
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "resume_sleep":
                    # This should end the conversation
                    return {"messages": [], "current_mode": "complete"}

        # Execute tools normally
        tool_node = SequentialToolNode(all_tools)
        result = tool_node.invoke(state)

        # Determine next mode based on last tool call
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "todo_write":
                    # After creating todos, go to execution
                    return {"messages": result["messages"], "current_mode": "execution"}
                elif tool_call["name"] == "clear_todos":
                    # After clearing todos, stay in planning mode
                    return {"messages": result["messages"], "current_mode": "planning"}

        # Default: continue based on current mode
        return {"messages": result["messages"], "current_mode": state.get("current_mode", "thinking")}

    # Graph definition
    graph = StateGraph(AgentState)
    graph.add_node("thinking", thinking_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("tools", tool_execution)

    # Set entry point to thinking mode
    graph.set_entry_point("thinking")

    # Define routing logic
    def route_from_thinking(state: AgentState) -> str:
        """Route from thinking to planning."""
        return "planning"

    def route_from_planning(state: AgentState) -> str:
        """Route from planning based on tool calls."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # Check if all todos are completed
        all_completed = all(todo.status == "completed" for todo in planning_toolkit.mission_todos)
        if planning_toolkit.mission_todos and all_completed:
            # All todos completed - route back to planning with notification
            return "planning"
        
        return "execution"

    def route_from_execution(state: AgentState) -> str:
        """Route from execution based on tool calls."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

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
    graph.add_conditional_edges("tools", route_from_tools)

    return graph.compile()