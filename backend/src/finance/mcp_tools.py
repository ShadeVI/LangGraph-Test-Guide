"""Puente MCP → LangChain: tools del servidor por protocolo stdio.

Cada ejecución abre UNA sesión contra ``python -m mcp_server.server``,
convierte sus tools a :class:`StructuredTool` y la cierra al terminar
(sesión por petición: sin estado compartido entre ejecuciones).

Por qué manual y no langchain-mcp-adapters: el adaptador exige
``langchain-core>=1.x`` y rompería los pines de este proyecto (Python 3.15).
Este puente solo depende del SDK ``mcp`` y de la API estable de tools.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, PrivateAttr, create_model

from config.logging_config import get_logger

logger = get_logger(__name__)
ROOT = Path(__file__).resolve().parents[2]

_JSON_TO_PYTHON: dict[str, Any] = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
}

_NO_ARGS_TITLE = "EmptyArgs"


def _args_model(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Construye el modelo pydantic de args desde el JSON Schema MCP.

    Args:
        tool_name: Nombre de la tool (para titular el modelo).
        schema: ``inputSchema`` tal como lo anuncia el servidor.

    Returns:
        Modelo con un campo por propiedad (requerido u opcional con None).
    """
    properties = (schema or {}).get("properties", {})
    required = set((schema or {}).get("required", []))
    fields: dict[str, Any] = {}
    for prop_name, prop in properties.items():
        py_type = _JSON_TO_PYTHON.get(prop.get("type", "string"), str)
        if prop_name in required:
            fields[prop_name] = (py_type, Field(description=prop.get("description", "")))
        else:
            fields[prop_name] = (py_type | None, Field(default=None))
    if not fields:
        return create_model(f"{tool_name}{_NO_ARGS_TITLE}")
    return create_model(f"{tool_name}Args", **fields)


class _MCPTool(StructuredTool):
    """StructuredTool cuya ejecución llama al servidor MCP por protocolo."""

    _session: ClientSession | None = PrivateAttr(default=None)

    def bind_session(self, session: ClientSession) -> "_MCPTool":
        """Asocia la sesión abierta (misma para todo el grafo).

        Fija además `coroutine`: sin él, `ainvoke` de langchain-core 0.3
        cae al path sync y la tool fallaría siempre en silencio.
        """
        self._session = session
        self.coroutine = self._session_call
        return self

    async def _session_call(self, *args: Any, **kwargs: Any) -> str:
        """Ejecuta la tool contra el servidor MCP por protocolo."""
        if self._session is None:
            raise RuntimeError(f"Tool MCP '{self.name}' sin sesión abierta.")
        logger.info("MCP → %s(%s)", self.name, kwargs)
        result = await self._session.call_tool(self.name, dict(kwargs or {}))
        texts = [c.text for c in result.content if hasattr(c, "text")]
        return "\n".join(texts)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return await self._session_call(*args, **kwargs)

    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise RuntimeError(
            f"Tool MCP '{self.name}' solo async: el grafo finance usa ainvoke."
        )


async def _convert(session: ClientSession) -> list[_MCPTool]:
    """Lista las tools del servidor y las convierte a LangChain."""
    listed = await session.list_tools()
    converted = []
    for tool in listed.tools:
        converted.append(
            _MCPTool(
                name=tool.name,
                description=tool.description or tool.name,
                args_schema=_args_model(tool.name, tool.inputSchema),
            ).bind_session(session)
        )
    logger.info("MCP: %d tools disponibles: %s", len(converted), [t.name for t in converted])
    return converted


@asynccontextmanager
async def mcp_session_tools() -> AsyncIterator[list[_MCPTool]]:
    """Abre el servidor MCP (subproceso stdio) y cede sus tools.

    Yields:
        Tools LangChain listas para ToolNode / bind_tools.
    """
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(ROOT)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield await _convert(session)
