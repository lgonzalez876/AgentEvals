import os

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI

from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "grok-4": "xai",
    "llama-3.3-70b-versatile": "groq",
    "deepseek-r1-distill-llama-70b": "groq",
    "gpt-4.1": "openai",
    "claude-opus-4-20250514": "anthropic",
    "gpt-4.1-nano-2025-04-14": "openai",
}

def enumerate_models():
    return list(MODELS.keys())

def get_model(
        model,
        temperature: float = 0.7
    ):
    match MODELS[model]:
        case "groq":
            provider = ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
        case "openai":
            provider = ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
        case "google":
            provider = ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")
        case "anthropic":
            provider = ChatAnthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
        case "xai":
            provider = ChatXAI
            api_key = os.getenv("XAI_API_KEY")
        case _:
            raise ValueError(f"Unsupported model provider: {MODELS[model]}")

    return provider(
        api_key=api_key,
        model_name=model,
        temperature=temperature,
    )
