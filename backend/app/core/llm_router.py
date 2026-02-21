"""
Digital FTE - LLM Router with Quota-Aware Fallback
Routes LLM calls through: Gemini Flash → Groq Llama 3.3 → Groq Mixtral → Groq Llama 3.1 8B
"""

import structlog
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger()

# ── Model definitions ───────────────────────────────

_MODELS = [
    {
        "name": "gemini-2.0-flash",
        "provider": "gemini",
        "rpm": 15,
        "rpd": 1500,
        "tpm": 1_000_000,
    },
    {
        "name": "llama-3.3-70b-versatile",
        "provider": "groq",
        "rpm": 30,
        "rpd": 14_400,
        "tpm": 131_072,
    },
    {
        "name": "mixtral-8x7b-32768",
        "provider": "groq",
        "rpm": 30,
        "rpd": 14_400,
        "tpm": 131_072,
    },
    {
        "name": "llama-3.1-8b-instant",
        "provider": "groq",
        "rpm": 30,
        "rpd": 14_400,
        "tpm": 131_072,
    },
]


def _build_llm(model_cfg: dict, temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Instantiate a LangChain chat model from config."""
    try:
        if model_cfg["provider"] == "gemini" and settings.GOOGLE_AI_API_KEY:
            return ChatGoogleGenerativeAI(
                model=model_cfg["name"],
                google_api_key=settings.GOOGLE_AI_API_KEY,
                temperature=temperature,
            )
        elif model_cfg["provider"] == "groq" and settings.GROQ_API_KEY:
            return ChatGroq(
                model=model_cfg["name"],
                groq_api_key=settings.GROQ_API_KEY,
                temperature=temperature,
            )
    except Exception as e:
        logger.warning("failed_to_build_llm", model=model_cfg["name"], error=str(e))
    return None


class LLMRouter:
    """Quota-aware LLM router with automatic fallback."""

    def __init__(self, temperature: float = 0.3):
        self.temperature = temperature
        self._models = _MODELS

    def get_llm(self, preferred_model: Optional[str] = None) -> BaseChatModel:
        """
        Return the best available LLM.
        Tries preferred model first, then walks the fallback chain.
        """
        order = list(self._models)
        if preferred_model:
            # Move preferred to front
            order.sort(key=lambda m: m["name"] != preferred_model)

        for cfg in order:
            llm = _build_llm(cfg, self.temperature)
            if llm is not None:
                logger.info("llm_selected", model=cfg["name"])
                return llm

        raise RuntimeError("No LLM provider is available. Check your API keys.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def invoke_with_fallback(self, messages, preferred_model: Optional[str] = None):
        """Invoke LLM with automatic retry and fallback."""
        order = list(self._models)
        if preferred_model:
            order.sort(key=lambda m: m["name"] != preferred_model)

        last_error = None
        for cfg in order:
            llm = _build_llm(cfg, self.temperature)
            if llm is None:
                continue
            try:
                result = await llm.ainvoke(messages)
                logger.info("llm_invoke_success", model=cfg["name"])
                return result
            except Exception as e:
                logger.warning("llm_invoke_failed", model=cfg["name"], error=str(e))
                last_error = e
                continue

        raise last_error or RuntimeError("All LLM providers failed.")


# Singleton
llm_router = LLMRouter()
