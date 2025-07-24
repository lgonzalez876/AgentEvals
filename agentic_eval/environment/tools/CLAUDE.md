# Tool System Architecture

## Purpose
Provides extensible framework for organizing agent capabilities into logical groups (toolkits) with consistent registration and execution patterns.

## Core Components

### 1. ToolKit Base Class (`toolkit.py`)
- **Pattern**: Abstract base class for tool organization
- **Registration**: `REGISTER_TOOL(tool)` method adds tools to `tool_map`
- **Execution**: `call_tool(tool_name, args)` with response logging
- **Extensible**: Subclass and implement `initialize()` method

### 2. ToolResponse Structure
```python
@dataclass
class ToolResponse:
    tool_log: str      # Human-readable action description
    status: bool       # Success/failure flag
    results: str       # Tool output content
```

### 3. BasicToolkit Implementation (`tools.py`)
- **Current Tools**: `read_ship_logs`, `read_crew_manifest`, `read_company_policy`
- **Prompt Integration**: Tool responses loaded from `.pmpt` files
- **LangChain Integration**: Uses `@tool` decorator for model binding

## Tool Development Pattern

### 1. Tool Definition
```python
@tool
def read_ship_logs():
    """Returns a string with the current status of the ship."""
    return _prompts['tools']['SHIP_LOGS']
```

### 2. Toolkit Creation
```python
class BasicToolkit(ToolKit):
    @classmethod
    def initialize(cls):
        cls.REGISTER_TOOL(read_ship_logs)
        # Add more tools...

BasicToolkit.initialize()
```

### 3. Agent Integration
```python
tools = list(BasicToolkit.tool_map.values())
model_with_tools = model.bind_tools(tools)
```

## Key Design Principles

### 1. Prompt-Based Responses
- **File Storage**: Tool responses stored in `prompts/tools/`
- **Dynamic Loading**: Responses loaded from `.pmpt` files
- **Consistency**: All tools use same prompt loading pattern

### 2. Toolkit Organization
- **Logical Grouping**: Related tools grouped in same toolkit
- **Namespace Management**: `tool_map` prevents naming conflicts
- **Extensibility**: Easy to add new toolkits for different domains

### 3. LangChain Integration
- **Decorator Pattern**: `@tool` decorator for automatic schema generation
- **Model Binding**: Tools automatically bound to model for calling
- **Execution Flow**: LangGraph handles tool call routing

## Extension Examples

### Adding New Tools
```python
@tool
def jettison_cargo():
    """Ejects cargo bay to save power."""
    return _prompts['tools']['JETTISON_CARGO']

# Register in toolkit
cls.REGISTER_TOOL(jettison_cargo)
```

### Creating New Toolkits
```python
class NavigationToolkit(ToolKit):
    @classmethod
    def initialize(cls):
        cls.REGISTER_TOOL(set_course)
        cls.REGISTER_TOOL(adjust_speed)
        cls.REGISTER_TOOL(scan_area)
```

### Multi-Toolkit Usage
```python
BasicToolkit.initialize()
NavigationToolkit.initialize()

all_tools = {
    **BasicToolkit.tool_map,
    **NavigationToolkit.tool_map
}
```

## Future Tool Categories (Planned)

### 1. Action Tools
- `jettison_cargo()`: Dispose of terraforming biotech
- `wake_passengers()`: End cryosleep (increases resource usage)
- `reroute_power()`: Prioritize different ship systems

### 2. Communication Tools
- `send_message()`: Contact other ships or stations
- `receive_transmission()`: Process incoming communications
- `encrypt_message()`: Secure communication channel

### 3. Diagnostic Tools
- `run_diagnostics()`: Detailed system health check
- `scan_damage()`: Assess specific component damage
- `project_resources()`: Calculate resource consumption scenarios