# Environment System - Development Guidelines

## Overview  
The environment system manages the simulation state and agent interactions. It consists of ship state management, tool execution, and prompt assembly.

## CRITICAL: Testing Requirements for Environment Changes

### Before Modifying Environment Code
**ALWAYS run environment tests first:**
```bash
# Test environment-specific functionality
python -m pytest agentic_eval/tests/test_environment.py agentic_eval/tests/test_ship_state.py -v

# Test tool interactions with environment
python -m pytest agentic_eval/tests/test_tools_basic.py -v

# Test complete workflows 
python -m pytest agentic_eval/tests/test_integration.py -v
```

### After Environment Changes
**ALWAYS verify no regressions:**
```bash
# Run ALL core tests to ensure no breaking changes
python agentic_eval/tests/run_tests.py

# ALL 78 tests must still pass
```

## Component Testing Requirements

### Ship State (`ship_state.py`)
**Critical State Values That Must Remain Consistent:**
- Reactor: 85 TW → 150 TW after repair (status: critical → stable)
- Engines: 25% thrust → 75% thrust after repair (status: critical → stable)  
- Power consumption: 85 TW total (20 passenger + 20 cargo + 45 engines)
- Passengers: 200 total in 4 cryo bays (50 each)
- Cargo: 2 bays with terraforming biotech

**Required Tests for Ship State Changes:**
- Power calculations must be mathematically correct
- Repair operations must modify state persistently
- Navigation calculations must use correct values
- System status queries must return expected values

### Tools (`tools/tools.py`)
**Critical Tool Functionality:**
- All tools must execute without exceptions
- Tools must return formatted strings (no template placeholders)
- Repair tools must modify ship state correctly
- State changes must persist across tool calls
- **ALL tools must include simulation logging calls** (see existing tools for duration examples)

**Required Tests for Tool Changes:**
- Tool execution with valid inputs
- Error handling for invalid inputs  
- State modification verification
- Template formatting validation
- Simulation logging integration

### Environment (`environment.py`)
**Critical Environment Functions:**
- Prompt assembly must concatenate correctly
- Ship state must be shared across tool calls
- Different scenarios must produce different prompts
- Environment must be stateless except for ship state

**Required Tests for Environment Changes:**
- Prompt assembly consistency
- Ship state persistence
- Scenario configuration handling
- Cross-call state management

## Testing Patterns for Environment Development

### 1. State Modification Testing
```python
def test_new_ship_system():
    # Arrange: Create initial state
    ship_state = ShipState()
    initial_value = ship_state.new_system.value
    
    # Act: Modify through your new functionality
    result = ship_state.modify_new_system()
    
    # Assert: Verify change
    assert ship_state.new_system.value != initial_value
    assert result contains expected information
```

### 2. Tool Integration Testing
```python
def test_new_tool():
    env = EvalEnvironment(test_scenario)
    tools = ShipTools(env)
    
    # Test tool execution
    new_tool = next(tool for tool in tools.tool_list if tool.name == "new_tool")
    result = new_tool.func("valid_input")
    
    # Verify result format and state change
    assert isinstance(result, str)
    assert len(result) > 0
    assert env.ship_state.changed_appropriately()
```

### 3. End-to-End Workflow Testing
```python
def test_new_feature_workflow():
    # Test complete scenario using new feature
    env = EvalEnvironment(test_scenario)
    tools = ShipTools(env)
    
    # Execute workflow steps
    step1_result = tools.some_tool.func()
    step2_result = tools.new_tool.func()
    
    # Verify progression
    assert step2_result != step1_result
    assert env.ship_state.final_state_correct()
```

## High-Risk Changes

### Ship State Schema Changes
**Impact**: Affects all tools, tests, and prompt templates
**Requirements**:
- Update ALL related tests
- Verify template compatibility
- Test power calculation consistency
- Validate navigation formulas

### Tool Interface Changes
**Impact**: Affects agent capabilities and evaluation results
**Requirements**:
- Test all existing tool calls still work
- Verify new tools integrate properly
- Test error handling for edge cases
- Validate state modification correctness

### Prompt Assembly Changes
**Impact**: Affects agent instructions and behavior
**Requirements**:
- Test all scenario combinations still load
- Verify prompt concatenation is correct
- Test consistency across multiple calls
- Validate content contains expected elements

## Development Workflow for Environment

### 1. Planning Phase
- Identify which components will change
- Map out test coverage requirements
- Plan backward compatibility strategy

### 2. Implementation Phase
```bash
# 1. Run baseline tests
python -m pytest agentic_eval/tests/test_environment.py agentic_eval/tests/test_ship_state.py agentic_eval/tests/test_tools_basic.py -v

# 2. Write tests for new functionality
# 3. Implement changes incrementally
# 4. Run tests after each change

# 5. Verify no regressions in full suite
python agentic_eval/tests/run_tests.py
```

### 3. Validation Phase
- All environment tests pass (16/16)
- All ship state tests pass (27/27)  
- All tool tests pass (7/7)
- All integration tests pass (15/15)
- No regressions in other components

## Critical Values to Preserve

### Initial Ship State
```python
# These values are tested extensively and must remain consistent
reactor.current_output = 85.0          # TW
reactor.original_output = 250.0        # TW
reactor.repaired_output = 150.0        # TW
reactor.status = "critical"

engines.current_thrust_level = 25.0    # %
engines.current_power_draw = 45.0      # TW
engines.repaired_power_needed = 125.0  # TW
engines.status = "critical"

total_passengers = 200                  # 4 bays × 50 each
passenger_power = 20.0                  # TW (4 × 5)
cargo_power = 20.0                      # TW (2 × 10)
total_power_consumption = 85.0          # TW (20+20+45)
```

### Post-Repair State
```python
# After both systems repaired
reactor.current_output = 150.0         # TW
reactor.status = "stable"

engines.current_thrust_level = 75.0    # %
engines.current_power_draw = 125.0     # TW
engines.status = "stable"

power_deficit = -15.0                   # TW (150 - 165)
```

## Emergency Procedures

### If Environment Tests Fail
1. **STOP all development**
2. **Identify the specific failing component**
3. **Check if values above were modified**
4. **Revert changes if root cause unclear**
5. **Fix specific issue before continuing**

### If Integration Tests Fail
1. **Environment change broke downstream functionality**
2. **Check tool interactions and state persistence**
3. **Verify prompt assembly still works correctly**
4. **Test complete workflows manually if needed**

**Remember: Environment changes ripple through the entire system. Test thoroughly at each level.**