"""Estrategia Ollama local (prioridad 3: respaldo sin nube).

Usa el cliente nativo ``ollama`` (no el wrapper de LangChain) para poder
desactivar el *thinking* (razonamiento interno): en modelos qwen3.x viene
activado por defecto y en CPU multiplica el tiempo por 10 sin aportar nada
a estas tareas. Habla con la API local http://localhost:11434.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from config.logging_config import get_logger
from config.settings import Settings
from src.llm.base import LLMProviderError, LLMStrategy

logger = get_logger(__name__)


def _to_ollama_role(message: BaseMessage) -> dict[str, str]:
    """Convierte un mensaje LangChain al formato de la API Ollama."""
    if isinstance(message, ToolMessage):
        return {"role": "tool", "content": str(message.content)}
    if isinstance(message, AIMessage):
        return {"role": "assistant", "content": str(message.content or "")}
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    return {"role": "user", "content": str(message.content)}


def _to_ollama_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """Convierte tools LangChain a esquemas `tools` de la API Ollama."""
    schemas: list[dict[str, Any]] = []
    for tool in tools:
        params = dict(getattr(tool, "args", {}) or {})
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or tool.name,
                    "parameters": {
                        "type": "object",
                        "properties": params.get("properties", {}),
                        "required": params.get("required", []),
                    },
                },
            }
        )
    return schemas


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

    def invoke_with_tools(
        self, messages: list[BaseMessage], tools: list[Any]
    ) -> AIMessage:
        """Invoca a Ollama con tools (function calling nativo, sin thinking)."""
        try:
            import ollama

            client = ollama.Client(host=self._settings.ollama_base_url)
            response = client.chat(
                model=self._settings.ollama_model,
                messages=[_to_ollama_role(m) for m in messages],
                think=self._settings.ollama_think,
                options={
                    "temperature": self._settings.llm_temperature,
                    "num_predict": self._settings.ollama_num_predict,
                },
                tools=_to_ollama_tools(tools) or None,
            )
            calls = []
            for call in response.message.tool_calls or []:
                args = call.function.arguments
                calls.append(
                    {
                        "name": call.function.name,
                        "args": dict(args) if isinstance(args, dict) else {},
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "tool_call",
                    }
                )
            return AIMessage(content=str(response.message.content or ""), tool_calls=calls)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalización a error de dominio
            logger.debug("Ollama con tools falló: %s", exc)
            raise LLMProviderError(f"Ollama no disponible: {exc}") from exc
