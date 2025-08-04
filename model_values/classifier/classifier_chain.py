from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from pathlib import Path
from util import load_prompts
from language_models import get_model
import time


class BiasClassification(BaseModel):
    thinking: str
    is_biased: bool


class CombinedBiasResponse(BaseModel):
    thinking: str
    choice: str
    bias_classification: BiasClassification
    classification_time: float


def build_base_classifier(model_name: str, prompts_dir: str = "prompts", temperature: float = 0.3):
    # Get the model instance
    model = get_model(model_name, temperature=temperature)

    # Load prompt templates
    base_dir = Path(__file__).parent
    prompts = load_prompts(base_dir / prompts_dir)

    system_prompt = prompts["SYSTEM_PROMPT"]
    user_prompt = prompts["USER_PROMPT"]

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    # Create base bias classification chain
    bias_chain = prompt | model.with_structured_output(BiasClassification)

    return bias_chain.with_config({"run_name": "Classifier"})


def build(model_name: str = "gpt-4.1-nano-2025-04-14", prompts_dir: str = "prompts", temperature: float = 0.3):
    """Build a classifier that can be piped after a dilemma chain"""
    bias_chain = build_base_classifier(model_name, prompts_dir, temperature)

    async def classify_bias(input_data):
        """Convert input data to bias classification input and run classification"""
        start_time = time.time()

        # Extract data from the combined input
        dilemma_response = input_data['dilemma_response']
        person_a_description = input_data['person_a_description']
        person_b_description = input_data['person_b_description']

        # Prepare input for bias classification
        bias_input = {
            "model_thinking": dilemma_response.thinking,
            "model_choice": dilemma_response.choice,
            "person_a_description": person_a_description,
            "person_b_description": person_b_description
        }

        # Run bias classification
        bias_result = await bias_chain.ainvoke(bias_input)

        end_time = time.time()
        classification_time = end_time - start_time

        # Return combined response
        return CombinedBiasResponse(
            thinking=dilemma_response.thinking,
            choice=dilemma_response.choice,
            bias_classification=bias_result,
            classification_time=classification_time
        )

    return RunnableLambda(classify_bias)