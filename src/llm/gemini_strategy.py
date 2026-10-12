"""Estrategia Google Gemini (prioridad 2) sobre el SDK oficial vigente.

Usa ``google-genai`` directamente (no el wrapper LangChain, anclado al SDK
descatalogado ``google-generativeai`` que rompe el function calling con los
modelos actuales: faltan *thought signatures*). Lecciones aplicadas:
thinking desactivado (rápido, sin firmas obligatorias) y schemas mínimos.
"""

from __future__ import annotations

import json
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
from src.llm.base import LLMConfigurationError, LLMProviderError, LLMStrategy

logger = get_logger(__name__)


def _client(settings: Settings) -> Any:
    """Crea el cliente genai (timeouts por defecto del SDK).

    Nota: no se fija `http_options.timeout` porque en la versión 2.29
    rompe el pool httpx ("client has been closed"); los reintentos y
    límites los gestiona el propio SDK y aquí se mapean a LLMProviderError.
    """
    from google import genai

    return genai.Client(api_key=settings.google_api_key)


def _gen_config(settings: Settings, tools: list[Any] | None = None) -> Any:
    """Config común: determinista, sin thinking, con tools opcionales."""
    from google.genai import types

    declarations = []
    for tool in tools or []:
        params = dict(getattr(tool, "args", {}) or {}).get("properties", {})
        required = dict(getattr(tool, "args", {}) or {}).get("required", [])
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or tool.name,
                parameters={"type": "object", "properties": params, "required": required},
            )
        )
    return types.GenerateContentConfig(
        temperature=settings.llm_temperature,
        # Dict, NO objeto ThinkingConfig: el objeto serializa campos que el
        # endpoint rechaza con 503 (verificado empíricamente).
        thinking_config={"thinking_budget": 0},
        tools=[types.Tool(function_declarations=declarations)] if declarations else None,
    )


def _to_contents(messages: list[BaseMessage]) -> tuple[str | None, list[Any]]:
    """Convierte historial LangChain a (system_instruction, contents) genai."""
    from google.genai import types

    system_parts: list[str] = []
    contents: list[Any] = []
    for message in messages:
        if isinstance(message, SystemMessage):
            system_parts.append(str(message.content))
        elif isinstance(message, ToolMessage):
            try:
                payload = json.loads(str(message.content))
                payload = payload if isinstance(payload, dict) else {"result": payload}
            except (json.JSONDecodeError, TypeError):
                payload = {"result": str(message.content)}
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=message.name or "tool", response=payload
                        )
                    ],
                )
            )
        elif isinstance(message, AIMessage):
            parts: list[Any] = []
            if message.content:
                parts.append(types.Part.from_text(text=str(message.content)))
            for call in message.tool_calls or []:
                parts.append(
                    types.Part.from_function_call(
                        name=call["name"], args=dict(call.get("args") or {})
                    )
                )
            contents.append(types.Content(role="model", parts=parts))
        elif isinstance(message, HumanMessage):
            contents.append(
                types.Content(
                    role="user", parts=[types.Part.from_text(text=str(message.content))]
                )
            )
        else:
            contents.append(
                types.Content(
                    role="user", parts=[types.Part.from_text(text=str(message.content))]
                )
            )
    system = "\n".join(system_parts) if system_parts else None
    return system, contents


def _to_ai_message(response: Any) -> AIMessage:
    """Convierte una respuesta genai a AIMessage (texto + tool_calls)."""
    calls = []
    for call in response.function_calls or []:
        calls.append(
            {
                "name": call.name,
                "args": dict(call.args or {}),
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call",
            }
        )
    return AIMessage(content=str(response.text or ""), tool_calls=calls)


class GeminiStrategy(LLMStrategy):
    """Proveedor Gemini vía SDK oficial ``google-genai``.

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
            response = _client(self._settings).models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=_gen_config(self._settings),
            )
            return str(response.text or "").strip()
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalización a error de dominio
            logger.debug("Gemini falló: %s", exc)
            raise LLMProviderError(f"Gemini no disponible: {exc}") from exc

    def invoke_with_tools(
        self, messages: list[BaseMessage], tools: list[Any]
    ) -> AIMessage:
        """Invoca a Gemini con function declarations (thinking desactivado)."""
        if not self._settings.google_api_key:
            raise LLMConfigurationError("GOOGLE_API_KEY no configurada (proveedor omitido).")
        try:
            system, contents = _to_contents(messages)
            config = _gen_config(self._settings, tools)
            if system:
                config.system_instruction = system
            response = _client(self._settings).models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
                config=config,
            )
            return _to_ai_message(response)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalización a error de dominio
            logger.debug("Gemini con tools falló: %s", exc)
            raise LLMProviderError(f"Gemini no disponible: {exc}") from exc
