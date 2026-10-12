"""Casos de uso de la API: ejecución completa y streaming por nodo.

Modos (variable de entorno ``API_MODE``):
  - ``demo`` (defecto): LLM guionizado; funciona sin API keys, ideal para la web.
  - ``live``: proveedores reales Groq → Gemini → Ollama (requiere keys).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from config.logging_config import get_logger
from config.settings import Settings
from src.graph.builder import ENTRY_POINT, build_graph_with_llm
from src.llm.base import LLMAllProvidersFailedError
from src.llm.factory import build_resilient_client
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState, initial_state
from api.demo_llm import build_demo_client
from api.schemas import RunResponse

logger = get_logger(__name__)

DEMO_MODE = "demo"
LIVE_MODE = "live"


def resolve_client(settings: Settings) -> tuple[ResilientLLMClient, str]:
    """Devuelve (cliente LLM, modo) según ``API_MODE``.

    Args:
        settings: Configuración de la aplicación.

    Returns:
        Cliente resiliente y "demo" o "live" (valor desconocido → demo + aviso).
    """
    mode = (settings.api_mode or DEMO_MODE).strip().lower()
    if mode == LIVE_MODE:
        return build_resilient_client(settings), LIVE_MODE
    if mode != DEMO_MODE:
        logger.warning("API_MODE=%r desconocido; se usa 'demo'.", settings.api_mode)
    return build_demo_client(), DEMO_MODE


def to_response(query: str, mode: str, final: GraphState) -> RunResponse:
    """Convierte el estado final del grafo en respuesta HTTP validada."""
    return RunResponse(
        query=query,
        mode=mode,
        kind="report",
        final_report=final.get("final_report", ""),
        path=list(final.get("path", [])),
        providers_used=list(final.get("providers_used", [])),
        errors=list(final.get("errors", [])),
        revision_count=final.get("revision_count", 0),
        current_step=final.get("current_step", "done"),
        editor_feedback=final.get("editor_feedback", ""),
        research_points=list(final.get("research_points", [])),
        draft=final.get("draft", ""),
    )


def run_pipeline(query: str, max_revisions: int, settings: Settings) -> RunResponse:
    """Ejecuta el grafo completo y devuelve el resultado (para POST /api/run).

    Raises:
        ValueError: Si la consulta está vacía.
        LLMAllProvidersFailedError: Si todos los proveedores fallan (modo live).
    """
    llm, mode = resolve_client(settings)
    logger.info("API: ejecución %s de %r (max_revisions=%d).", mode, query, max_revisions)
    graph = build_graph_with_llm(llm, max_revisions)
    final: GraphState = graph.invoke(initial_state(query))
    logger.info("API: fin %s, ruta=%s.", mode, " -> ".join(final.get("path", [])))
    return to_response(query, mode, final)


def _summarize_node(node: str, patch: dict[str, Any]) -> str:
    """Resume en lenguaje humano lo que hizo un nodo (para la demo en vivo).

    Args:
        node: Nombre del nodo ejecutado.
        patch: Patch que devolvió (métricas + trazabilidad acumulada).

    Returns:
        Frase corta y explicativa, p. ej. "Borrador Nº 2 de 62 caracteres".
    """
    providers = patch.get("providers_used", [])
    last = providers[-1] if providers else "?"
    if node == "researcher":
        n = len(patch.get("research_points", []))
        return f"{n} puntos clave extraídos de la consulta (vía {last})"
    if node == "writer":
        revs = patch.get("revision_count", 0)
        size = len(patch.get("draft", ""))
        return f"Borrador Nº {revs + 1} redactado, {size} caracteres (vía {last})"
    if node == "editor":
        if patch.get("needs_revision"):
            return f"Veredicto: REVISAR — {patch.get('editor_feedback', '')} (vía {last})"
        size = len(patch.get("final_report", ""))
        return f"Veredicto: APROBADO, informe de {size} caracteres (vía {last})"
    return f"Paso {patch.get('current_step', node)} (vía {last})"


def _route_after(node: str, patch: dict[str, Any], max_revisions: int) -> dict[str, str] | None:
    """Describe la transición que sigue a un nodo (historial lineal de la demo).

    Refleja la topología de ``builder``: researcher→writer y writer→editor son
    fijas; tras el editor decide el veredicto con el mismo criterio que el
    router (duplicación intencional y documentada: el stream no ejecuta el
    router, solo narra lo que este decidirá).

    Args:
        node: Nodo recién ejecutado.
        patch: Su patch (veredicto, contador, feedback).
        max_revisions: Tope del ciclo editor→writer.

    Returns:
        Dict ``{from, to, detail}`` o None si el nodo no transiciona.
    """
    if node == "researcher":
        n = len(patch.get("research_points", []))
        return {"from": "researcher", "to": "writer", "detail": f"{n} puntos listos"}
    if node == "writer":
        revs = patch.get("revision_count", 0)
        return {"from": "writer", "to": "editor", "detail": f"borrador Nº {revs + 1} terminado"}
    if node == "editor":
        if patch.get("needs_revision"):
            used = patch.get("revision_count", 0)
            if used < max_revisions:
                return {
                    "from": "editor",
                    "to": "writer",
                    "detail": f"REVISAR ({used + 1}/{max_revisions}): {patch.get('editor_feedback', '')}",
                }
            return {
                "from": "editor",
                "to": "end",
                "detail": f"límite de revisiones (máx. {max_revisions}): se publica el último borrador",
            }
        return {"from": "editor", "to": "end", "detail": "APROBADO: informe final"}
    return None


def _sse(event: str, payload: dict[str, Any]) -> str:
    """Formatea un evento Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_pipeline(query: str, max_revisions: int, settings: Settings) -> Iterator[str]:
    """Genera eventos SSE por nodo usando ``graph.stream()`` (GET /api/run/stream).

    Emite `start`, por cada nodo un `node` seguido de su `route` (transición
    narrada), y un `done` final con el :class:`RunResponse` completo. El `final` se
    reconstruye fusionando patches (cada patch ya trae acumulados trazables).
    """
    llm, mode = resolve_client(settings)
    logger.info("API: streaming %s de %r.", mode, query)
    graph = build_graph_with_llm(llm, max_revisions)
    yield _sse("start", {"query": query, "mode": mode, "max_revisions": max_revisions, "entry": ENTRY_POINT, "label": f'"{query}" (modo {mode}, máx. {max_revisions} revisiones)'})
    merged: dict[str, Any] = {"query": query}
    try:
        for chunk in graph.stream(initial_state(query)):
            node, patch = next(iter(chunk.items()))
            merged.update(patch)
            yield _sse(
                "node",
                {
                    "node": node,
                    "current_step": patch.get("current_step"),
                    "summary": _summarize_node(node, patch),
                    "needs_revision": patch.get("needs_revision"),
                    "providers_used": patch.get("providers_used", []),
                    "errors": patch.get("errors", []),
                    "path": patch.get("path", []),
                    # Estado post-nodo (merged ya incorpora este patch):
                    # es exactamente lo que leerá el siguiente agente.
                    "snapshot": {
                        "kind": "report",
                        "query": query,
                        "research_points": merged.get("research_points", []),
                        "draft": merged.get("draft", ""),
                        "final_report": merged.get("final_report", ""),
                        "revision_count": merged.get("revision_count", 0),
                        "needs_revision": merged.get("needs_revision", False),
                        "editor_feedback": merged.get("editor_feedback", ""),
                        "path": merged.get("path", []),
                        "providers_used": merged.get("providers_used", []),
                        "errors": merged.get("errors", []),
                        "current_step": merged.get("current_step", ""),
                    },
                },
            )
            route = _route_after(node, patch, max_revisions)
            if route is not None:
                yield _sse("route", route)
    except LLMAllProvidersFailedError as exc:
        yield _sse("error", {"detail": str(exc)[:300]})
        return
    final = GraphState(**merged)  # type: ignore[typeddict-unknown-key]
    yield _sse("done", to_response(query, mode, final).model_dump())
