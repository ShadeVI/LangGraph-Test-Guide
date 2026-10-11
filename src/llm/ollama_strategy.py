"""Estrategia Ollama local (prioridad 3: respaldo sin nube).

Usa el cliente nativo ``ollama`` (no el wrapper de LangChain) para poder
desactivar el *thinking* (razonamiento interno): en modelos qwen3.x viene
activado por defecto y en CPU multiplica el tiempo por 10 sin aportar nada
a estas tareas. Habla con la API local http://localhost:11434.
"""

from __future__ import annotations

from config.logging_config import get_logger
from config.settings import Settings
from src.llm.base import LLMProviderError, LLMStrategy

logger = get_logger(__name__)


class OllamaStrategy(LLMStrategy):
    """Proveedor Ollama local vía API nativa ``/api/chat`` (sin API key).

    Args:
        settings: Configuración con modelo, URL base, temperatura,
            tope de tokens y flag de thinking.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        """Returns: Identificador ``"ollama"``."""
        return "ollama"

    def generate(self, prompt: str) -> str:
        """Invoca al modelo local con thinking desactivado y tope de tokens.

        Raises:
            LLMProviderError: Si Ollama no está en ejecución o el modelo falta.
        """
        try:
            import ollama

            client = ollama.Client(host=self._settings.ollama_base_url)
            response = client.chat(
                model=self._settings.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                think=self._settings.ollama_think,  # False = respuesta directa
                options={
                    "temperature": self._settings.llm_temperature,
                    "num_predict": self._settings.ollama_num_predict,
                },
            )
            return str(response.message.content or "").strip()
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalización a error de dominio
            logger.debug("Ollama falló: %s", exc)
            raise LLMProviderError(f"Ollama no disponible: {exc}") from exc
