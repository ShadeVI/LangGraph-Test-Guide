"""Estrategia Google Gemini (prioridad 2)."""

from __future__ import annotations

from typing import Any

from config.logging_config import get_logger
from config.settings import Settings
from src.llm.base import LLMConfigurationError, LLMProviderError, LLMStrategy

logger = get_logger(__name__)


def _build_chat_gemini(settings: Settings) -> Any:
    """Construye ChatGoogleGenerativeAI compatible con SDK viejo y nuevo."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    fields = set(ChatGoogleGenerativeAI.model_fields.keys())
    kwargs: dict[str, Any] = {
        "model": settings.gemini_model,
        "temperature": settings.llm_temperature,
    }
    if "api_key" in fields:
        kwargs["api_key"] = settings.google_api_key
    else:  # langchain-google-genai < 2.1 (usa google_api_key + timeout)
        kwargs["google_api_key"] = settings.google_api_key
    if "request_timeout" in fields:
        kwargs["request_timeout"] = settings.llm_timeout
    elif "timeout" in fields:
        kwargs["timeout"] = settings.llm_timeout
    return ChatGoogleGenerativeAI(**kwargs)


class GeminiStrategy(LLMStrategy):
    """Proveedor Gemini vía ``langchain-google-genai``.

    Args:
        settings: Configuración con API key, modelo, temperatura y timeout.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        """Returns: Identificador ``"gemini"``."""
        return "gemini"

    def generate(self, prompt: str) -> str:
        """Invoca al modelo Gemini configurado.

        Raises:
            LLMProviderError: Si falta la API key o la API falla.
        """
        if not self._settings.google_api_key:
            raise LLMConfigurationError("GOOGLE_API_KEY no configurada (proveedor omitido).")
        try:
            chat = _build_chat_gemini(self._settings)
            return str(chat.invoke(prompt).content)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalización a error de dominio
            logger.debug("Gemini falló: %s", exc)
            raise LLMProviderError(f"Gemini no disponible: {exc}") from exc
