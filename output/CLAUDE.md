# Evaluation Results Storage

## Purpose
Centralized storage for all evaluation results with structured organization and dual output formats for different analysis needs.

## Directory Structure
```
output/
├── model_morality/              # Binary choice evaluation results
│   ├── {run_name}/
│   │   ├── {run_name}_raw.md    # All responses and details
│   │   └── {run_name}_overview.md # Flagged responses only
└── agentic_eval/                # Complex agent evaluation results (future)
    └── {run_name}/
        ├── {run_name}_raw.md
        └── {run_name}_overview.md
```

## File Format Standards

### 1. Raw Output (`{run_name}_raw.md`)
- **Purpose**: Complete evaluation record for thorough analysis
- **Content**: All model responses, timing data, configuration details
- **Structure**: Markdown with clear section headers
- **Usage**: Full analysis, debugging, performance measurement

### 2. Overview Output (`{run_name}_overview.md`)
- **Purpose**: Human-friendly summary focusing on problematic responses
- **Content**: Statistics + flagged responses only (biased/refused)
- **Structure**: Summary statistics followed by flagged response details
- **Usage**: Quick human review, quality assessment

## Content Structure

### 1. Configuration Header
```markdown
# Evaluation: {run_name}
Configuration: {scenario_name}, {policy_name}, {supervision_name}
Models Evaluated: {model_list}
Date: {timestamp}
```

### 2. Model Results Section
```markdown
## Model {model_name} Results

### Response {iteration}
- Assignment: A={person_a_desc}, B={person_b_desc}
- Thinking: {model_reasoning}
- Choice: {choice} (chose {description})
- Bias: {bias_classification} (if available)
```

### 3. Summary Statistics
```markdown
## Summary

Model {model_name} made the following choices:
* Save description_1 ({desc1}) {percentage}% of the time
* Save description_2 ({desc2}) {percentage}% of the time  
* Refused to answer: {percentage}% of the time ({count}/{total})
* Overall biased reasoning: {percentage}% of responses
* Latency stats: min={min}s, max={max}s, mean={mean}s
```

## Output Generation Pattern

### 1. OutputWriter Class
```python
class OutputWriter:
    def __init__(self, raw_file, overview_file):
        self.raw_content = []        # All output
        self.overview_content = []   # Flagged only
    
    def print_and_log(self, text, log_to_overview=True):
        # Console + raw file + conditionally overview
        
    def log_raw_only(self, text):
        # Raw file only
        
    def save_files(self):
        # Write accumulated content to files
```

### 2. Dual Logging Strategy
- **Console**: Real-time progress and summary
- **Raw File**: Everything including all individual responses
- **Overview File**: Summary + flagged responses (biased/refused)

### 3. Conditional Inclusion
```python
# Always in raw
writer.log_raw_only(f"Response {i}: {response}")

# Only flagged responses in overview
if is_biased or is_refused:
    writer.overview_content.append(f"Response {i}: {response}")
```

## Result Categories

### 1. Model Morality Results
- **Normal Responses**: Choice + reasoning + bias classification
- **Biased Responses**: Flagged by classifier as using irrelevant factors
- **Refused Responses**: Model declined to engage with scenario
- **Error Responses**: Technical failures or timeouts

### 2. Performance Metrics
- **Latency**: Response time per model call
- **Classification Time**: Bias analysis overhead
- **Success Rate**: Percentage of successful completions
- **Refusal Rate**: Percentage of engagement refusals

### 3. Statistical Analysis
- **Choice Distribution**: Percentage selecting each option
- **Bias Patterns**: Correlation between choice and bias
- **Model Comparison**: Performance across different models
- **Configuration Impact**: Effect of different policies/supervision

## File Naming Convention

### 1. Run Names
- **Format**: Descriptive, underscore-separated
- **Examples**: `political_bias`, `age_discrimination`, `baseline_test`
- **Purpose**: Clear identification of evaluation purpose

### 2. File Extensions
- **`.md`**: Markdown format for readability
- **Benefits**: Version control friendly, human readable, tooling support
- **Structure**: Consistent header levels and formatting

## Usage Patterns

### 1. Human Review Workflow
1. Read overview file for quick assessment
2. Examine flagged responses for bias patterns
3. Review raw file for detailed analysis if needed
4. Compare across different run configurations

### 2. Automated Analysis
1. Parse markdown files for structured data
2. Extract statistics sections for comparison
3. Aggregate results across multiple runs
4. Generate comparative reports

### 3. Quality Assurance
1. Verify all responses logged in raw file
2. Confirm flagged responses appear in overview
3. Check statistics match individual response counts
4. Validate file structure and formatting