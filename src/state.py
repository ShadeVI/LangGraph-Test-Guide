"""Estado compartido que viaja por el StateGraph (contrato tipado estricto)."""

from __future__ import annotations

from typing import TypedDict


class GraphState(TypedDict, total=False):
    """Estado del grafo multi-agente.

    Attributes:
        query: Consulta original del usuario (única entrada requerida).
        research_points: Puntos clave estructurados del Analizador.
        draft: Borrador técnico del Sintetizador.
        final_report: Informe Markdown final del Reviewer.
        providers_used: Trazabilidad de qué proveedor resolvió cada llamada.
        errors: Fallos de proveedor capturados (no fatales, para observabilidad).
        current_step: Etapa actual del pipeline (analyzer/synthesizer/reviewer/done).
        needs_revision: Veredicto del Reviewer; True reencamina a synthesizer (ciclo).
        revision_count: Nº de revisiones ya realizadas (acota el ciclo).
        reviewer_feedback: Motivo del veredicto REVISAR (guía la reescritura).
        path: Nodos recorridos en orden (evidencia la ruta no lineal).
    """

    query: str
    research_points: list[str]
    draft: str
    final_report: str
    providers_used: list[str]
    errors: list[str]
    current_step: str
    needs_revision: bool
    revision_count: int
    reviewer_feedback: str
    path: list[str]


def initial_state(query: str) -> GraphState:
    """Crea el estado inicial del grafo a partir de la consulta.

    Args:
        query: Pregunta o tema del usuario. No debe estar vacía.

    Returns:
        Estado inicial válido para :class:`StateGraph`.

    Raises:
        ValueError: Si la consulta está vacía o solo tiene espacios.
    """
    if not query or not query.strip():
        raise ValueError("La consulta no puede estar vacía.")
    return GraphState(
        query=query.strip(),
        research_points=[],
        draft="",
        final_report="",
        providers_used=[],
        errors=[],
        current_step="started",
        needs_revision=False,
        revision_count=0,
        reviewer_feedback="",
        path=[],
    )
