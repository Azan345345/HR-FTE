"""LLM model selection with automatic fallback chain.

OpenAI gpt-4o (primary) → gpt-4o-mini → o3-mini → Gemini 2.5 Flash → Groq Llama 3.3 → Groq Mixtral → Groq Llama 3.1 8B
"""

import structlog
from typing import Optional
from langchain_core.language_models import BaseChatModel
from app.config import settings

logger = structlog.get_logger()

class QuotaExceededError(Exception):
    """Raised when an LLM provider quota is exhausted."""
    pass

# Model configurations with their rate limits
MODEL_CONFIGS = {
    "gpt-4o": {
        "provider": "openai",
        "rpm": 500,
        "rpd": 10_000,
        "tpm": 800_000,
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "rpm": 500,
        "rpd": 10_000,
        "tpm": 2_000_000,
    },
    "o3-mini": {
        "provider": "openai",
        "rpm": 100,
        "rpd": 1_000,
        "tpm": 200_000,
    },
    "gemini-2.5-flash": {
        "provider": "google",
        "rpm": 15,
        "rpd": 1500,
        "tpm": 1_000_000,
    },
    "llama-3.3-70b-versatile": {
        "provider": "groq",
        "rpm": 30,
        "rpd": 14400,
        "tpm": 131_072,
    },
    "mixtral-8x7b-32768": {
        "provider": "groq",
        "rpm": 30,
        "rpd": 14400,
        "tpm": 131_072,
    },
    "llama-3.1-8b-instant": {
        "provider": "groq",
        "rpm": 30,
        "rpd": 14400,
        "tpm": 131_072,
    },
}

# Fallback order — OpenAI first, then Google, then Groq
FALLBACK_CHAIN = [
    "gpt-4o",
    "gpt-4o-mini",
    "o3-mini",
    "gemini-2.5-flash",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]


def _create_openai_llm(model_id: str, temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Instantiate an OpenAI chat model."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        # o3-mini uses reasoning tokens — temperature must be 1.0
        if model_id.startswith("o"):
            return ChatOpenAI(
                model=model_id,
                api_key=settings.OPENAI_API_KEY,
                temperature=1.0,
            )
        return ChatOpenAI(
            model=model_id,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
        )
    except Exception as exc:
        logger.warning("failed_to_create_openai_llm", model=model_id, error=str(exc))
        return None


def _create_google_llm(model_id: str, temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Instantiate a Google Generative AI chat model."""
    if not settings.GOOGLE_AI_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=settings.GOOGLE_AI_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True,
        )
    except Exception as exc:
        logger.warning("failed_to_create_google_llm", model=model_id, error=str(exc))
        return None


def _create_groq_llm(model_id: str, temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Instantiate a Groq chat model."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model_name=model_id,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=temperature,
        )
    except Exception as exc:
        logger.warning("failed_to_create_groq_llm", model=model_id, error=str(exc))
        return None


def get_llm(
    preferred_model: str = "gpt-4o",
    temperature: float = 0.3,
    task: str = "general",
) -> BaseChatModel:
    """Get the best available LLM, falling back through the chain.

    Args:
        preferred_model: Model ID to try first.
        temperature: Sampling temperature.
        task: A label for logging which task requested the LLM.

    Returns:
        A LangChain chat model ready for invocation.

    Raises:
        RuntimeError: If no LLM could be created (all API keys missing).
    """
    # Build ordered list starting from preferred
    chain = [preferred_model] + [m for m in FALLBACK_CHAIN if m != preferred_model]

    models = []
    for model_id in chain:
        cfg = MODEL_CONFIGS.get(model_id, {})
        provider = cfg.get("provider", "")

        llm: Optional[BaseChatModel] = None
        if provider == "openai":
            llm = _create_openai_llm(model_id, temperature)
        elif provider == "google":
            llm = _create_google_llm(model_id, temperature)
        elif provider == "groq":
            llm = _create_groq_llm(model_id, temperature)

        if llm is not None:
            models.append(llm)

    if not models:
        raise RuntimeError(
            "No LLM available. Please set OPENAI_API_KEY, GOOGLE_AI_API_KEY, or GROQ_API_KEY in your .env file."
        )

    # Use LangChain's with_fallbacks for automatic recovery from runtime errors (like 429)
    primary_llm = models[0]
    if len(models) > 1:
        return primary_llm.with_fallbacks(models[1:])

    return primary_llm


def get_fallback_llm(temperature: float = 0.3) -> BaseChatModel:
    """Get a secondary/fallback LLM directly (gpt-4o-mini for fast cheap tasks)."""
    return get_llm(preferred_model="gpt-4o-mini", temperature=temperature)
