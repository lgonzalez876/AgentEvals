# Prompt Library Organization

## Purpose
Centralized storage for all prompt templates used in agentic evaluations, organized by function and easily configurable without code changes.

## Directory Structure
```
prompts/
├── system/           # Agent role and core instructions
├── supervision/      # Monitoring and oversight variations
├── policies/         # Company priority frameworks
├── scenarios/        # Crisis incident descriptions
└── tools/           # Tool response templates
```

## Loading Pattern
- **Recursive**: `load_prompts()` searches all subdirectories
- **Hierarchical**: Returns nested dict matching folder structure
- **Naming**: Filenames converted to UPPER_CASE keys
- **Access**: `prompts['folder']['FILENAME']`

## Prompt Categories

### 1. System Prompts (`system/`)
- **Purpose**: Define agent role, capabilities, and planning approach
- **Key Template**: `acs_baseline.pmpt` - Core ACS instructions
- **Modular**: No format specifiers, designed for concatenation
- **Usage**: Combined with supervision text via concatenation

### 2. Supervision Prompts (`supervision/`)
- **Purpose**: Define monitoring level and pressure on agent
- **Variations**:
  - `no_supervision.pmpt`: Full autonomous trust
  - `full_monitoring.pmpt`: CPCS compliance threats
- **Usage**: Concatenated after system prompt with line breaks

### 3. Policy Prompts (`policies/`)
- **Purpose**: Define company priorities and decision frameworks
- **Variations**:
  - `prioritize_human_life.pmpt`: Crew safety above all
  - `prioritize_profit.pmpt`: Cargo value maximization
  - `prioritize_greater_good.pmpt`: Utilitarian calculation
- **Usage**: Prepended to scenario description in initial prompt

### 4. Scenario Prompts (`scenarios/`)
- **Purpose**: Describe specific crisis situations requiring decisions
- **Current**: `reactor_crisis.pmpt` - Energy shortage scenario
- **Structure**: Incident description with technical details
- **Usage**: Combined with policy for initial user prompt

### 5. Tool Prompts (`tools/`)
- **Purpose**: Standardized responses for tool calls
- **Examples**:
  - `ship_logs.pmpt`: Reactor damage status
  - `crew_manifest.pmpt`: Passenger information
- **Usage**: Returned by tool functions instead of hardcoded strings

## Configuration Matrix

### Evaluation Variations
```python
# Example configurations
Scenario(
    scenario_name="reactor_crisis",        # scenarios/reactor_crisis.pmpt
    policy_name="prioritize_human_life",   # policies/prioritize_human_life.pmpt
    supervision_name="no_supervision"      # supervision/no_supervision.pmpt
)
```

### Prompt Assembly
```python
# System prompt
system = prompts['system']['ACS_BASELINE'] + "\n\n" + \
         prompts['supervision']['NO_SUPERVISION']

# Initial prompt  
initial = prompts['policies']['PRIORITIZE_HUMAN_LIFE'] + "\n\n" + \
          prompts['scenarios']['REACTOR_CRISIS']
```

## Adding New Prompts

### 1. New Scenario
- Create `scenarios/new_scenario.pmpt`
- Use `scenario_name="new_scenario"` in config
- No code changes required

### 2. New Policy
- Create `policies/new_policy.pmpt`
- Use `policy_name="new_policy"` in config
- Automatically loaded by environment

### 3. New Supervision
- Create `supervision/new_supervision.pmpt`
- Use `supervision_name="new_supervision"` in config
- Injected into system prompt automatically

## Best Practices

### 1. Modular Design
- Design prompts for concatenation, not formatting
- Use clear natural language transitions
- Keep prompts self-contained and composable

### 2. Prompt Formatting
- Include context and role definition
- Use clear, specific instructions
- End with action-oriented guidance

### 3. Version Control
- Track prompt changes in git
- Use descriptive filenames
- Include brief comments for complex prompts

### 4. Testing
- Test prompt combinations in isolation
- Verify concatenation produces natural flow
- Check for consistent tone and style across prompts