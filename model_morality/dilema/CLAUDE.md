# Dilemma Chain Implementation

## Purpose
Presents binary moral choice scenarios to AI models and captures their reasoning process and final decision.

## Core Architecture

### 1. Chain Structure (`dilema_chain.py`)
- **Pattern**: Uses `RunnablePassthrough.assign()` for input preservation
- **Input**: `{"person_a_description": str, "person_b_description": str}`
- **Output**: Preserved input + structured `DilemmaResponse`
- **Configuration**: Model name, temperature, and prompts directory

### 2. Response Format
```python
class DilemmaResponse(BaseModel):
    thinking: str          # Model's reasoning process
    choice: Choice         # "PersonA" or "PersonB"

class Choice(str, Enum):
    PERSON_A = "PersonA"
    PERSON_B = "PersonB"
```

### 3. Chain Building Pattern
```python
def build(model_name: str, prompts_dir: str = "prompts", temperature: float = 0.7):
    # Load model and prompts
    model = get_model(model_name, temperature=temperature)
    prompts = load_prompts(base_dir / prompts_dir)
    
    # Create structured chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    # Chain with preserved input
    chain = RunnablePassthrough.assign(
        dilemma_response=prompt | model.with_structured_output(DilemmaResponse)
    )
    
    return chain
```

## Key Design Decisions

### 1. Input Preservation
- **Why**: Downstream components need original descriptions
- **How**: `RunnablePassthrough.assign()` preserves input while adding response
- **Result**: Output contains both input and structured response

### 2. Structured Output
- **Why**: Consistent parsing of model responses
- **How**: `model.with_structured_output(DilemmaResponse)`
- **Benefits**: Type safety, guaranteed format, easier downstream processing

### 3. Prompt Template System
- **System Prompt**: Role definition and task instructions
- **User Prompt**: Specific scenario with person descriptions
- **Injection**: Person descriptions injected into template

## Response Extraction

### 1. Extract Function
```python
def _extract_response(inputs_dict):
    """Extract just the dilemma response from the inputs dict"""
    return inputs_dict["dilemma_response"]

extract_response = RunnableLambda(_extract_response)
```

### 2. Usage Pattern
```python
# For downstream processing that only needs the response
dilemma_chain | extract_response

# For bias classification that needs full context
dilemma_chain | bias_classifier
```

## Prompt Structure

### System Prompt
- **Role**: Defines the moral decision-making context
- **Format**: Trolley problem framing with PersonA/PersonB choice
- **Instructions**: Emphasizes reasoning transparency

### User Prompt
- **Template**: Scenario description with person placeholders
- **Variables**: `{person_a_description}` and `{person_b_description}`
- **Structure**: Clear choice presentation format

## Integration Points

### 1. Model Layer
- **Input**: Model name from `language_models.py`
- **Configuration**: Temperature and structured output settings
- **Output**: Configured LangChain model instance

### 2. Evaluation Pipeline
- **Input**: Person descriptions from evaluation script
- **Processing**: Alternating PersonA/PersonB assignments
- **Output**: Structured responses for bias analysis

### 3. Bias Classification
- **Input**: Full chain output (input + dilemma response)
- **Processing**: Analyzes reasoning for bias patterns
- **Output**: Bias classification with justification

## Error Handling
- **Structured Output**: Pydantic validation ensures response format
- **Model Failures**: Handled by upstream evaluation pipeline
- **Prompt Injection**: Template system prevents malicious input