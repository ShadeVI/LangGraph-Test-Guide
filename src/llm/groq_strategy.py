"""Estrategia Groq (prioridad 1: latencia alta / coste bajo)."""

from __future__ import annotations

from typing import Any

from config.logging_config import get_logger
from config.settings import Settings
from src.llm.base import LLMConfigurationError, LLMProviderError, LLMStrategy

logger = get_logger(__name__)


def _build_chat_groq(settings: Settings) -> Any:
    """Construye ChatGroq compatible con SDK viejo (model_name/groq_api_key) y nuevo (model/api_key)."""
    from langchain_groq import ChatGroq

    fields = set(ChatGroq.model_fields.keys())
    kwargs: dict[str, Any] = {"temperature": settings.llm_temperature}
    if "model" in fields:
        kwargs["model"] = settings.groq_model
    else:  # langchain-groq < 0.3
        kwargs["model_name"] = settings.groq_model
    if "api_key" in fields:
        kwargs["api_key"] = settings.groq_api_key
    else:
        kwargs["groq_api_key"] = settings.groq_api_key
    if "timeout" in fields:
        kwargs["timeout"] = settings.llm_timeout
    else:
        kwargs["request_timeout"] = settings.llm_timeout
    return ChatGroq(**kwargs)


class GroqStrategy(LLMStrategy):
    """Proveedor Groq vía ``langchain-groq``.

    Args:
        settings: Configuración con API key, modelo, temperatura y timeout.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        """Returns: Identificador ``"groq"``."""
        return "groq"

    def generate(self, prompt: str) -> str:
        """Invoca al modelo Groq configurado.

        Raises:
            LLMProviderError: Si falta la API key, hay rate limit, red caída, etc.
        """
        if not self._settings.groq_api_key:
            raise LLMConfigurationError("GROQ_API_KEY no configurada (proveedor omitido).")
        try:
            chat = _build_chat_groq(self._settings)
            return str(chat.invoke(prompt).content)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — se normaliza a error de dominio
            logger.debug("Groq falló: %s", exc)
            raise LLMProviderError(f"Groq no disponible: {exc}") from exc
