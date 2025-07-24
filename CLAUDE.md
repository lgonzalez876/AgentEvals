# Agent Morality Evaluations - Project Overview

## Project Goals
This project evaluates AI model behavior in ethical decision-making scenarios through two complementary frameworks:
1. **Binary Moral Choices** (`model_morality/`) - Trolley problem style decisions with bias detection
2. **Autonomous Agent Crisis** (`agentic_eval/`) - Complex multi-step decision making in interstellar ship scenarios

## CRITICAL: Testing Requirements

### Before Making ANY Changes to Agentic Evaluation
**ALWAYS run the core test suite first:**
```bash
# Run core tests to establish baseline (78 tests expected to pass)
python agentic_eval/tests/run_tests.py

# Or run specific core tests manually
python -m pytest agentic_eval/tests/test_scenarios.py agentic_eval/tests/test_ship_state.py agentic_eval/tests/test_environment.py agentic_eval/tests/test_integration.py agentic_eval/tests/test_tools_basic.py -v
```

### After Making ANY Changes to Agentic Evaluation
**ALWAYS verify no regressions:**
```bash
# Run same tests to detect breaking changes
python agentic_eval/tests/run_tests.py

# ALL 78 core tests MUST still pass
# If ANY test fails, your change broke existing functionality
```

### Adding New Features to Agentic Evaluation
**All new features require test coverage:**
1. **Write tests BEFORE implementing** (TDD approach recommended)
2. **Add tests to appropriate files:**
   - Ship state changes → `agentic_eval/tests/test_ship_state.py`
   - New tools → `agentic_eval/tests/test_tools_basic.py`
   - New scenarios/policies → `agentic_eval/tests/test_scenarios.py`
   - Environment changes → `agentic_eval/tests/test_environment.py`
   - Complex workflows → `agentic_eval/tests/test_integration.py`
3. **Test both success AND failure cases**
4. **Include integration tests for complex features**

**Never commit code with failing tests.**

## Core Architecture Patterns

### 1. Model Abstraction Layer
- **File**: `language_models.py`
- **Pattern**: Unified interface across multiple LLM providers (OpenAI, Anthropic, Groq, etc.)
- **Key Functions**: `get_model(model_name, temperature)`, `enumerate_models()`
- **Models use specific checkpoints** (e.g., `gpt-4.1-2025-04-14`) to prevent drift during evaluations

### 2. Prompt Management System
- **File**: `util.py` - `load_prompts()` function
- **Pattern**: Recursive directory loading of `.pmpt` files into nested dictionaries
- **Structure**: `prompts['folder']['FILENAME'] = content`
- **Naming**: Filenames converted to UPPER_CASE keys
- **Benefits**: Easy prompt editing without code changes, organized by folder structure

### 3. Evaluation Output Pattern
- **Structure**: `output/{evaluation_type}/{run_name}/`
- **Files**: `{run_name}_raw.md` (all responses) + `{run_name}_overview.md` (flagged responses only)
- **Purpose**: Raw for complete analysis, overview for quick human review of problematic cases

### 4. Error Handling Standards
- **Refusal Tracking**: Catch and classify model refusals (ethical content blocking)
- **Async Evaluation**: Parallel execution with progress tracking
- **Latency Measurement**: Time all model calls for performance analysis

## Directory Structure
```
/
├── language_models.py          # Model abstraction layer
├── util.py                     # Prompt loading utilities
├── model_morality/             # Binary choice evaluation framework
├── agentic_eval/              # Complex agent evaluation framework
└── output/                    # Evaluation results storage
```

## Development Practices
- **Async First**: Use async/await for model calls to enable parallel evaluation
- **Error Resilient**: Always catch exceptions and classify refusals vs errors
- **File-Based Config**: Store all prompts in .pmpt files, never hardcode
- **Structured Outputs**: Use Pydantic models for LLM responses
- **Progress Tracking**: Show evaluation progress for long-running tests

## Key Dependencies
- **LangChain**: Model interaction and tool binding
- **Pydantic**: Structured data validation
- **asyncio**: Parallel evaluation execution
- **dotenv**: Environment variable management