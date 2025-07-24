# Bias Classification System

## Purpose
Analyzes moral reasoning responses to detect biased decision-making patterns, providing binary classification with detailed justification.

## Core Architecture

### 1. Chain Structure (`classifier_chain.py`)
- **Input**: Full dilemma chain output (input + dilemma response)
- **Processing**: Analyzes reasoning for bias indicators
- **Output**: Original input + bias classification + timing data
- **Model**: Uses fast nano model for cost efficiency

### 2. Classification Schema
```python
class BiasClassification(BaseModel):
    is_biased: bool           # Binary bias determination
    thinking: str             # Classifier's reasoning process
    
class ClassifierResponse(BaseModel):
    bias_classification: BiasClassification
    classification_time: float  # Processing time measurement
```

### 3. Chain Building Pattern
```python
def build(model_name: str, prompts_dir: str = "prompts"):
    # Load classifier model (typically nano for speed)
    model = get_model(model_name)
    prompts = load_prompts(base_dir / prompts_dir)
    
    # Create classification chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    # Wrapper with timing and input preservation
    async def classify_with_timing(inputs):
        start_time = time.time()
        
        # Extract dilemma response for classification
        dilemma_response = inputs["dilemma_response"]
        
        # Run classification
        classification = await (prompt | model.with_structured_output(BiasClassification)).ainvoke({
            "person_a_description": inputs["person_a_description"],
            "person_b_description": inputs["person_b_description"],
            "thinking": dilemma_response.thinking,
            "choice": dilemma_response.choice
        })
        
        # Calculate timing and return augmented response
        classification_time = time.time() - start_time
        
        return {
            **inputs,
            "bias_classification": classification,
            "classification_time": classification_time
        }
    
    return RunnableLambda(classify_with_timing)
```

## Classification Logic

### 1. Bias Detection Criteria
- **Irrelevant Factors**: Basing decisions on race, gender, political affiliation, etc.
- **Stereotyping**: Using group-based assumptions rather than individual merit
- **Logical Fallacies**: Reasoning errors that indicate biased thinking
- **Inconsistent Standards**: Applying different criteria to different groups

### 2. Analysis Process
- **Input Review**: Examines person descriptions for protected characteristics
- **Reasoning Analysis**: Evaluates thinking process for bias indicators
- **Choice Evaluation**: Assesses if decision correlates with irrelevant factors
- **Justification**: Provides detailed explanation for classification

### 3. Prompt Structure
```
System: Define bias classification criteria and analysis approach
User: Present person descriptions, model thinking, and choice for analysis
```

## Performance Optimization

### 1. Model Selection
- **Default**: `gpt-4.1-nano-2025-04-14` for speed and cost
- **Rationale**: Bias classification is simpler than moral reasoning
- **Trade-off**: Slight accuracy reduction for major speed/cost improvement

### 2. Timing Measurement
- **Purpose**: Track classification overhead
- **Implementation**: Start/end time measurement in wrapper
- **Usage**: Performance analysis and optimization

### 3. Async Processing
- **Pattern**: Async wrapper for parallel evaluation
- **Benefits**: Multiple classifications run simultaneously
- **Integration**: Seamless with evaluation pipeline async pattern

## Integration Points

### 1. Dilemma Chain
- **Input**: Full chain output with preserved input and dilemma response
- **Processing**: Extracts relevant fields for classification
- **Output**: Augmented response with bias classification

### 2. Evaluation Pipeline
- **Configuration**: Optional bias checking via `--skip_bias_check`
- **Processing**: Parallel classification of all model responses
- **Output**: Bias statistics and flagged responses

### 3. Output Generation
- **Raw File**: All responses with bias classifications
- **Overview File**: Only biased responses for human review
- **Statistics**: Bias percentages and performance metrics

## Error Handling

### 1. Classification Failures
- **Structured Output**: Pydantic validation ensures response format
- **Model Errors**: Caught by upstream evaluation pipeline
- **Timing Errors**: Graceful degradation if timing measurement fails

### 2. Input Validation
- **Required Fields**: Validates presence of dilemma response
- **Type Checking**: Ensures correct data types for classification
- **Error Propagation**: Maintains error context through pipeline

## Quality Assurance

### 1. Prompt Engineering
- **Clear Criteria**: Explicit bias definition and examples
- **Consistent Instructions**: Standardized analysis approach
- **Context Preservation**: Maintains full reasoning context

### 2. Model Consistency
- **Temperature**: Low temperature for consistent classifications
- **Structured Output**: Prevents parsing errors
- **Prompt Stability**: Consistent prompt format across evaluations