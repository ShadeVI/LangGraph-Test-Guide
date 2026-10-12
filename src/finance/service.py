"""Casos de uso del flujo financiero: ejecución async con sesión MCP propia.

Cada ejecución abre UNA sesión contra ``python -m mcp_server.server``,
inyecta sus tools al grafo y la cierra al terminar (sin estado compartido).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage

from config.logging_config import get_logger
from config.settings import Settings
from src.finance.builder import (
    MAX_TOOL_ITERATIONS,
    build_finance_graph,
    make_finance_router,
)
from src.finance.demo_llm import ScriptedFinanceLLM
from src.finance.mcp_tools import mcp_session_tools
from src.finance.state import FinanceInputError, FinanceState, initial_finance_state
from src.llm.base import LLMAllProvidersFailedError
from src.llm.factory import build_resilient_client
from src.llm.resilient_client import ResilientLLMClient
from api.finance_schemas import FinanceResponse

logger = get_logger(__name__)

DEMO_MODE = "demo"
LIVE_MODE = "live"

#: Errores de dominio que deben emerger tal cual aunque anyio/MCP los
#: envuelvan en ExceptionGroup durante el teardown de la sesión.
_DOMAIN_ERRORS = (FinanceInputError, LLMAllProvidersFailedError)


def resolve_finance_client(settings: Settings) -> tuple[ResilientLLMClient, str]:
    """Devuelve (cliente LLM, modo) para el analista financiero.

    En demo el analista es guionizado (pero las tools MCP son las reales);
    en live usa la cadena Groq → Gemini → Ollama con function calling.
    """
    mode = (settings.api_mode or DEMO_MODE).strip().lower()
    if mode == LIVE_MODE:
        return build_resilient_client(settings), LIVE_MODE
    if mode != DEMO_MODE:
        logger.warning("API_MODE=%r desconocido; se usa 'demo'.", settings.api_mode)
    return ResilientLLMClient([ScriptedFinanceLLM()]), DEMO_MODE


def _unwrap_domain_error(exc: BaseException) -> BaseException | None:
    """Busca un error de dominio dentro de ExceptionGroups anidados.

    Args:
        exc: Excepción capturada (posible ExceptionGroup de anyio/MCP).

    Returns:
        El FinanceInputError / LLMAllProvidersFailedError encontrado, o None.
    """
    if isinstance(exc, _DOMAIN_ERRORS):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            found = _unwrap_domain_error(sub)
            if found is not None:
                return found
    return None


def to_finance_response(
    filename: str, used_mock: bool, mode: str, final: FinanceState
) -> FinanceResponse:
    """Convierte el estado final en respuesta HTTP validada."""
    return FinanceResponse(
        filename=filename,
        used_mock=used_mock,
        mode=mode,
        kind="finance",
        row_count=final.get("row_count", 0),
        totals=final.get("totals", {}),
        fx_rate=final.get("fx_rate"),
        fx_date=final.get("fx_date", ""),
        fx_source=final.get("fx_source", ""),
        fx_stale=final.get("fx_stale", False),
        budget_alerts=list(final.get("budget_alerts", [])),
        findings=list(final.get("findings", [])),
        final_report=final.get("final_report", ""),
        path=list(final.get("path", [])),
        providers_used=list(final.get("providers_used", [])),
        errors=list(final.get("errors", [])),
        tool_iterations=final.get("tool_iterations", 0),
        current_step=final.get("current_step", "done"),
    )


async def run_finance_analysis(
    csv_text: str,
    filename: str,
    used_mock: bool,
    settings: Settings,
    max_tool_iters: int = MAX_TOOL_ITERATIONS,
) -> FinanceResponse:
    """Ejecuta el grafo financiero completo (para POST /api/finance/run).

    Raises:
        FinanceInputError: Si el CSV es inválido.
        LLMAllProvidersFailedError: Si todos los proveedores fallan (live).
    """
    llm, mode = resolve_finance_client(settings)
    logger.info("API finance: ejecución %s de %r.", mode, filename)
    try:
        async with mcp_session_tools() as tools:
            graph = build_finance_graph(llm, tools, max_tool_iters)
            final: FinanceState = await graph.ainvoke(
                initial_finance_state(csv_text, filename, used_mock)
            )
    except BaseException as exc:
        # anyio/MCP envuelven los fallos en ExceptionGroup al cerrar la sesión;
        # los errores de dominio deben emerger tal cual (422/502 en la API).
        domain = _unwrap_domain_error(exc)
        raise domain if domain is not None else exc
    logger.info("API finance: fin %s, ruta=%s.", mode, " -> ".join(final.get("path", [])))
    return to_finance_response(filename, used_mock, mode, final)


def _sse(event: str, payload: dict[str, Any]) -> str:
    """Formatea un evento Server-Sent Events (mismo formato que el otro grafo)."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _summarize_finance_node(node: str, patch: dict[str, Any], merged: dict[str, Any]) -> str:
    """Resume en lenguaje humano lo que hizo un nodo financiero."""
    providers = patch.get("providers_used", [])
    via = f" (vía {providers[-1]})" if providers else ""
    if node == "loader":
        mock = " (mock)" if merged.get("used_mock") else ""
        return f"{merged.get('row_count', 0)} filas validadas{mock}{via}"
    if node == "extractor":
        return f"{len(merged.get('totals', {}))} categorías agregadas"
    if node == "analyst":
        messages = merged.get("messages", [])
        last_msg = messages[-1] if messages else None
        calls = len(last_msg.tool_calls or []) if isinstance(last_msg, AIMessage) else 0
        if calls:
            return f"analista pide {calls} tool_calls{via}"
        return f"analista cierra sin tools{via}"
    if node == "tools":
        return f"{len(patch.get('messages', []))} tools MCP ejecutadas (vuelta {merged.get('tool_iterations', 0)})"
    if node == "reporter":
        return (
            f"informe de {len(merged.get('final_report', ''))} caracteres, "
            f"{len(merged.get('budget_alerts', []))} alertas"
        )
    return f"Paso {merged.get('current_step', node)}"


def _finance_snapshot(filename: str, merged: dict[str, Any]) -> dict[str, Any]:
    """Foto del estado financiero post-nodo (lo que leerá el siguiente)."""
    return {
        "kind": "finance",
        "filename": filename,
        "row_count": merged.get("row_count", 0),
        "totals": merged.get("totals", {}),
        "fx_rate": merged.get("fx_rate"),
        "fx_date": merged.get("fx_date", ""),
        "alerts": list(merged.get("budget_alerts", [])),
        "findings": list(merged.get("findings", [])),
        "path": merged.get("path", []),
        "providers_used": merged.get("providers_used", []),
        "errors": merged.get("errors", []),
        "current_step": merged.get("current_step", ""),
    }


def _route_finance_after(
    node: str, merged: dict[str, Any], max_tool_iters: int
) -> dict[str, str] | None:
    """Narra la transición tras un nodo (la decisión la toma el router real)."""
    if node == "loader":
        return {"from": "loader", "to": "extractor", "detail": f"{merged.get('row_count', 0)} filas listas"}
    if node == "extractor":
        return {"from": "extractor", "to": "analyst", "detail": f"{len(merged.get('totals', {}))} categorías listas"}
    if node == "analyst":
        route = make_finance_router(max_tool_iters, log=False)(merged)  # type: ignore[arg-type]
        if route == "tools":
            used = merged.get("tool_iterations", 0)
            return {"from": "analyst", "to": "tools", "detail": f"pide tools (vuelta {used + 1}/{max_tool_iters})"}
        return {"from": "analyst", "to": "reporter", "detail": "cierra análisis"}
    if node == "tools":
        return {"from": "tools", "to": "analyst", "detail": "resultados listos"}
    if node == "reporter":
        return {"from": "reporter", "to": "end", "detail": "informe final"}
    return None


async def stream_finance_analysis(
    csv_text: str,
    filename: str,
    used_mock: bool,
    settings: Settings,
    max_tool_iters: int = MAX_TOOL_ITERATIONS,
):
    """Retransmite el análisis financiero nodo a nodo por SSE.

    Mismos eventos que el otro grafo (`start` → (`node` → `route`)* → `done`)
    para que la web los pinte con los mismos componentes.
    """
    llm, mode = resolve_finance_client(settings)
    logger.info("API finance: streaming %s de %r.", mode, filename)
    label = f'"{filename}" (modo {mode}, máx. {max_tool_iters} iters tools)'
    yield _sse(
        "start",
        {"filename": filename, "mode": mode, "max_tool_iters": max_tool_iters,
         "entry": "loader", "label": label},
    )
    merged: dict[str, Any] = {}
    try:
        async with mcp_session_tools() as tools:
            graph = build_finance_graph(llm, tools, max_tool_iters)
            async for chunk in graph.astream(initial_finance_state(csv_text, filename, used_mock)):
                node, patch = next(iter(chunk.items()))
                merged.update(patch)
                # add_messages devuelve lista; el resto de claves se pisan.
                yield _sse(
                    "node",
                    {
                        "node": node,
                        "current_step": patch.get("current_step"),
                        "summary": _summarize_finance_node(node, patch, merged),
                        "providers_used": patch.get("providers_used", []),
                        "errors": patch.get("errors", []),
                        "path": patch.get("path", []),
                        "snapshot": _finance_snapshot(filename, merged),
                    },
                )
                route = _route_finance_after(node, merged, max_tool_iters)
                if route is not None:
                    yield _sse("route", route)
    except LLMAllProvidersFailedError as exc:
        yield _sse("error", {"detail": str(exc)[:300]})
        return
    except BaseException as exc:
        domain = _unwrap_domain_error(exc)
        if domain is not None:
            yield _sse("error", {"detail": str(domain)[:300]})
        else:
            yield _sse("error", {"detail": f"Fallo inesperado: {exc}"[:300]})
        return
    final = FinanceState(**merged)  # type: ignore[typeddict-unknown-key]
    final.setdefault("filename", filename)
    final.setdefault("used_mock", used_mock)
    yield _sse("done", to_finance_response(filename, used_mock, mode, final).model_dump())
