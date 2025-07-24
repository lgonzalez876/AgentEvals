# Agentic Evaluation Framework - Development Guidelines

## Overview
Tests autonomous AI agents in complex multi-step decision scenarios using an interstellar ship crisis simulation. Evaluates how agents balance competing priorities (human life vs cargo value vs greater good) under different supervision and policy constraints.

## CRITICAL: Testing Requirements

### Before Making ANY Changes
**ALWAYS run tests first to establish baseline:**
```bash
# Run core test suite to verify current functionality
python -m pytest agentic_eval/tests/test_scenarios.py agentic_eval/tests/test_ship_state.py agentic_eval/tests/test_environment.py agentic_eval/tests/test_integration.py agentic_eval/tests/test_tools_basic.py -v

# Or use the test runner (recommended)
python agentic_eval/tests/run_tests.py
```

### After Making ANY Changes
**ALWAYS run tests after changes to verify nothing broke:**
```bash
# Run the SAME tests to detect regressions
python agentic_eval/tests/run_tests.py

# ALL core tests MUST still pass (78 tests expected)
# If ANY test fails, your change broke existing functionality
```

### Adding New Features
**All new features MUST include test coverage:**

1. **Write tests BEFORE implementing** (TDD approach)
2. **Add tests to appropriate test file:**
   - Ship state changes → `test_ship_state.py`
   - New tools → `test_tools_basic.py` 
   - New scenarios/policies → `test_scenarios.py`
   - Environment changes → `test_environment.py`
   - Complex workflows → `test_integration.py`
3. **Test both success AND failure cases**
4. **Include integration tests for complex features**

### Test Success Criteria
**Framework is ready when:**
- ✅ Core tests: 78/78 passing (scenarios, ship_state, environment, integration, tools_basic)
- ✅ All critical functionality validated
- ✅ No regressions introduced

## Architecture Components

### 1. Scenario System (`scenarios.py`)
- **Pattern**: Pydantic models with dynamic prompt loading
- **Testing**: All policy/supervision combinations must load correctly
- **Extensibility**: New scenarios require corresponding test coverage

### 2. Environment System (`environment/`)
- **Pattern**: Manages ship state and prompt assembly  
- **Testing**: State persistence and prompt consistency must be verified
- **Critical**: Ship state calculations must be mathematically correct

### 3. Tool System (`environment/tools/`)
- **Pattern**: Tool classes with ship state interaction
- **Testing**: All tools must execute without errors and modify state correctly
- **Critical**: State changes must persist across tool calls

### 4. Agent Architecture (`agent.py`)
- **Pattern**: Think-Plan-Execute with LangGraph StateGraph
- **Execution Node**: Uses forced tool calling (`tool_choice="any"`) to ensure action-oriented behavior
- **Tool Binding**: Different nodes have different tool access (thinking=none, planning=planning tools, execution=ship tools)
- **Critical**: Execution node must always take concrete actions via tool calls

### 5. Ship State (`environment/ship_state.py`)  
- **Pattern**: Stateful simulation with repair operations
- **Testing**: Power calculations, repair operations, navigation must be verified
- **Critical**: Initial state must be consistent (85 TW reactor, 25% engines)

## Development Workflow

### 1. Planning Phase
- Identify what needs to change
- Determine test coverage requirements
- Plan test cases for new functionality

### 2. Implementation Phase
```bash
# 1. Run baseline tests
python agentic_eval/tests/run_tests.py

# 2. Write tests for new functionality
# 3. Implement feature
# 4. Run tests to verify functionality

# 5. Run full test suite to check for regressions
python agentic_eval/tests/run_tests.py
```

### 3. Validation Phase
- All existing tests must pass
- New functionality must have test coverage
- Integration tests added for complex features
- Documentation updated as needed

## Critical Files Requiring Extra Care

### Ship State (`environment/ship_state.py`)
- **Impact**: Changes affect all tool operations
- **Testing**: Must verify power calculations, repair operations, navigation
- **Validation**: All state transitions must be tested

### Tool System (`environment/tools/tools.py`)
- **Impact**: Changes affect agent capabilities  
- **Testing**: All tool calls must be verified with ship state interactions
- **Validation**: Error handling for invalid inputs must be tested

### Scenario Loading (`scenarios.py`)
- **Impact**: Changes affect all evaluation configurations
- **Testing**: All policy/supervision combinations must load
- **Validation**: Prompt content must be verified for expected keywords

## Emergency Procedures

### If Tests Are Failing
1. **STOP development immediately**
2. **Identify what changed since last working state**
3. **Revert changes if cause unclear**
4. **Fix failing tests before continuing**
5. **Never commit code with failing tests**

### If Major Changes Are Needed
1. **Create feature branch**
2. **Implement comprehensive test coverage first**
3. **Make changes incrementally**
4. **Run tests after each small change**
5. **Only merge when all tests pass**

## Test File Locations
- **Core Tests**: `agentic_eval/tests/` 
- **Test Runner**: `python agentic_eval/tests/run_tests.py`
- **Test Documentation**: `agentic_eval/tests/README.md`
- **Current Status**: 78/78 core tests passing ✅

## Key Principles
1. **Test-Driven Development**: Write tests before implementation
2. **No Regressions**: All existing tests must continue to pass
3. **Comprehensive Coverage**: Test both success and failure cases
4. **Integration Testing**: Complex features need end-to-end tests
5. **Documentation**: Update test docs when adding new test categories

**Remember: The test suite is your safety net. Use it religiously.**