from typing import List, Any
import logging
from abc import ABC, abstractmethod
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from pydantic import BaseModel, Field

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
                    logger.info(error_content)

                    error_message = ToolMessage(
                        content=error_content,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    tool_messages.append(error_message)
            else:
                # Handle unknown tool
                error_content = f"Unknown tool: {tool_name}"
                logger.info(error_content)

                error_message = ToolMessage(
                    content=error_content,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                tool_messages.append(error_message)

        return {"messages": tool_messages}

class ToolKit(ABC):
    """Base class for organizing tools into logical groups with selective exposure."""
    
    def __init__(self):
        self.tool_list = []  # Default tool list for simple toolkits
        self._create_tools()
    
    @abstractmethod
    def _create_tools(self):
        """Create and store tool instances. Must be implemented by subclasses."""
        pass
    
    def get_available_tools(self) -> List[Any]:
        """Return list of tools that should be exposed based on current state.
        
        Default implementation returns self.tool_list.
        Override for selective exposure based on state.
        """
        return self.tool_list
