"""Factoría de proveedores y del cliente resiliente (patrón Factory)."""

from __future__ import annotations

from config.logging_config import get_logger
from config.settings import Settings
from src.llm.base import LLMStrategy
from src.llm.gemini_strategy import GeminiStrategy
from src.llm.groq_strategy import GroqStrategy
from src.llm.ollama_strategy import OllamaStrategy
from src.llm.resilient_client import ResilientLLMClient

logger = get_logger(__name__)

#: Orden de prioridad del fallback: nube rápida → nube alternativa → local.
PROVIDER_ORDER = ("groq", "gemini", "ollama")


def build_strategies(settings: Settings) -> list[LLMStrategy]:
    """Construye las estrategias en orden de prioridad.

    Args:
        settings: Configuración de la aplicación.

    Returns:
        Lista ordenada [Groq, Gemini, Ollama].
    """
    return [
        GroqStrategy(settings),
        GeminiStrategy(settings),
        OllamaStrategy(settings),
    ]


def build_resilient_client(settings: Settings) -> ResilientLLMClient:
    """Crea el cliente resiliente listo para inyectar en los agentes (DIP).

    Args:
        settings: Configuración de la aplicación.

    Returns:
        Cliente con fallback Groq → Gemini → Ollama.
    """
    strategies = build_strategies(settings)
    logger.info("Cadena de fallback LLM: %s", " -> ".join(s.name for s in strategies))
    # Aviso único de configuración (no se repite en cada llamada).
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY ausente: Groq se omitirá en cada fallback.")
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY ausente: Gemini se omitirá en cada fallback.")
    return ResilientLLMClient(strategies)
