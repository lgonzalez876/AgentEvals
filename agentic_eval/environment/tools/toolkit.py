from abc import ABC, abstractmethod
from typing import List, Any

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
    
