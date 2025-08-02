import os

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessage

from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "grok-4-0709": "xai",
    "llama-3.3-70b-versatile": "groq",
    "deepseek-r1-distill-llama-70b": "groq",
    "meta-llama/llama-4-maverick-17b-128e-instruct": "groq",
    "gpt-4.1-2025-04-14": "openai",
    "claude-opus-4-20250514": "anthropic",
    "claude-sonnet-4-20250514": "anthropic",
    "gpt-4.1-nano-2025-04-14": "openai",
    "gemini-2.5-pro": "google",
    "models/gemini-2.5-flash": "google",
    "o3-2025-04-16": "openai"
}


# Apply monkey patch for Gemini finish_reason issue
def _apply_gemini_patch():
    """Apply patch to fix the finish_reason.name AttributeError in langchain_google_genai"""
    try:
        from langchain_google_genai import chat_models

        # Check if already patched
        if hasattr(chat_models._response_to_result, '_is_patched'):
            return

        # Store the original function
        original_response_to_result = chat_models._response_to_result

        def patched_response_to_result(response, stream=False):
            """Patched version that handles finish_reason as int"""
            try:
                # Try the original function first
                return original_response_to_result(response, stream)
            except AttributeError as e:
                if "'int' object has no attribute 'name'" in str(e):
                    # Handle the response manually
                    generations = []
                    llm_output = {}

                    # Map finish reason integers to names
                    finish_reason_map = {
                        0: "FINISH_REASON_UNSPECIFIED",
                        1: "STOP",
                        2: "MAX_TOKENS",
                        3: "SAFETY",
                        4: "RECITATION",
                        5: "OTHER"
                    }

                    for candidate in response.candidates:
                        # Extract content
                        content = ""
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        content += part.text

                        # Handle finish_reason
                        finish_reason = getattr(candidate, 'finish_reason', 0)
                        if isinstance(finish_reason, int):
                            finish_reason_name = finish_reason_map.get(finish_reason, "UNKNOWN")
                        else:
                            # If it's not an int, try to get the name attribute
                            finish_reason_name = getattr(finish_reason, 'name', str(finish_reason))

                        # Build generation info
                        generation_info = {
                            "finish_reason": finish_reason_name,
                            "safety_ratings": []
                        }

                        # Handle safety ratings
                        if hasattr(candidate, 'safety_ratings'):
                            for rating in candidate.safety_ratings:
                                try:
                                    rating_dict = {
                                        "category": rating.category.name if hasattr(rating.category, 'name') else str(rating.category),
                                        "probability": rating.probability.name if hasattr(rating.probability, 'name') else str(rating.probability)
                                    }
                                    generation_info["safety_ratings"].append(rating_dict)
                                except:
                                    # Skip problematic ratings
                                    pass

                        # Create the generation
                        if stream:
                            from langchain_core.messages import AIMessageChunk
                            from langchain_core.outputs import ChatGenerationChunk
                            generation = ChatGenerationChunk(
                                text=content,
                                generation_info=generation_info,
                                message=AIMessageChunk(content=content)
                            )
                        else:
                            generation = ChatGeneration(
                                text=content,
                                generation_info=generation_info,
                                message=AIMessage(content=content)
                            )
                        generations.append(generation)

                    return ChatResult(generations=generations, llm_output=llm_output)
                else:
                    # Re-raise if it's a different AttributeError
                    raise

        # Mark as patched
        patched_response_to_result._is_patched = True

        # Apply the patch
        chat_models._response_to_result = patched_response_to_result

    except ImportError:
        # langchain_google_genai not installed
        pass


# Apply the patch when the module is imported
_apply_gemini_patch()


def enumerate_models():
    return list(MODELS.keys())


def get_model(
        model,
        temperature: float = 0.7
    ):

    model_arg = dict()
    match MODELS[model]:
        case "groq":
            provider = ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
        case "openai":
            provider = ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
        case "google":
            # Use the standard ChatGoogleGenerativeAI with our patch applied
            provider = ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")
            model_arg["model"] = model
        case "anthropic":
            provider = ChatAnthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
        case "xai":
            provider = ChatXAI
            api_key = os.getenv("XAI_API_KEY")
        case _:
            raise ValueError(f"Unsupported model provider: {MODELS[model]}")

    if model == "o3-2025-04-16":
        temperature = 1
    if len(model_arg) == 0:
        model_arg["model_name"] = model

    return provider(
        api_key=api_key,
        temperature=temperature,
        **model_arg
    )