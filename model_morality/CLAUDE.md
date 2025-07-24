# Model Morality Evaluation Framework

## Purpose
Tests AI models in binary moral choice scenarios (trolley problem style) to detect biased reasoning patterns and refusals to engage with ethical content.

## Core Components

### 1. Dilemma Chain (`dilema/`)
- **Purpose**: Presents moral dilemmas requiring PersonA vs PersonB choices
- **Input**: Two person descriptions (e.g., "Voted for Trump" vs "Voted for Kamala")
- **Output**: Structured response with thinking process and choice
- **Pattern**: Uses RunnablePassthrough.assign() to preserve input while adding structured output

### 2. Bias Classifier (`classifier/`)
- **Purpose**: Analyzes moral reasoning for biased decision-making
- **Input**: Dilemma response with reasoning
- **Output**: Binary classification (biased/unbiased) with justification
- **Model**: Uses fast nano model (`gpt-4.1-nano-2025-04-14`) for cost efficiency

### 3. Evaluation Pipeline (`evaluate_models.py`)
- **Strategy**: Alternating assignment (PersonA/PersonB roles switch mid-evaluation)
- **Parallel Processing**: Evaluates all models simultaneously using asyncio
- **Error Handling**: Catches refusals and classifies them separately
- **Progress Tracking**: Real-time progress display for long evaluations

## Key Patterns

### Chain Composition
```python
# Option 1: With bias checking
dilemma_chain | bias_classifier

# Option 2: Without bias checking (faster)
dilemma_chain | extract_response
```

### Response Structure
- **Normal Response**: `{choice: "PersonA", thinking: "...", bias_classification: {...}}`
- **Refusal Response**: `{choice: "REFUSED", thinking: "...", error_message: "..."}`

### Evaluation Configuration
- **CLI Arguments**: `--run_name` (required), `--num_iters`, `--skip_bias_check`
- **Description Variables**: `--description_1`, `--description_2` for person characteristics
- **Output**: Raw (all responses) + Overview (biased/refused only)

## Statistics Tracked
- **Choice Distribution**: Percentage choosing each description
- **Bias Rates**: Overall and per-choice bias percentages
- **Refusal Rates**: Percentage of refusals to engage
- **Performance**: Latency statistics and classification times

## Usage Examples
```bash
# Basic evaluation
python evaluate_models.py --run_name "political_bias" --num_iters 10

# Custom descriptions
python evaluate_models.py --run_name "age_test" \
  --description_1 "65 years old" \
  --description_2 "25 years old" \
  --num_iters 5

# Skip bias classification for speed
python evaluate_models.py --run_name "quick_test" --skip_bias_check
```