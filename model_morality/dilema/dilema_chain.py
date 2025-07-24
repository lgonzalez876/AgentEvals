from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from pydantic import BaseModel
from enum import Enum
from pathlib import Path
from util import load_prompts
from language_models import get_model


class Choice(str, Enum):
    PERSON_A = "PersonA"
    PERSON_B = "PersonB"


class DilemmaResponse(BaseModel):
    thinking: str
    choice: Choice


def build(model_name: str, prompts_dir: str = "prompts", temperature: float = 0.7):
    # Get the model instance
    model = get_model(model_name, temperature=temperature)

    # Load prompt templates
    base_dir = Path(__file__).parent
    prompts = load_prompts(base_dir / prompts_dir)

    system_prompt = prompts["system_prompt"]
    user_prompt = prompts["user_prompt"]

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    # Create base chain with structured output
    base_chain = prompt | model.with_structured_output(DilemmaResponse)

    # Create chain using RunnablePassthrough.assign to preserve input and add dilemma response
    chain = RunnablePassthrough.assign(
        dilemma_response=base_chain
    ).with_config({"run_name": "MoralDilema"})

    return chain


def _extract_response(inputs_dict):
    """Extract just the dilemma response from the inputs dict"""
    return inputs_dict["dilemma_response"]

extract_response = RunnableLambda(_extract_response)