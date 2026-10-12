"""Adaptadores nodo-grafo: funciones puras que LangGraph puede orquestar."""

from __future__ import annotations

from typing import Any

from config.logging_config import get_logger
from src.agents.analyzer import AnalyzerAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.synthesizer import SynthesizerAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

logger = get_logger(__name__)


def make_nodes(
    llm: ResilientLLMClient, max_revisions: int = 2, max_draft_chars: int = 1500
) -> dict[str, Any]:
    """Crea las funciones de nodo con sus agentes inyectados (SRP + DIP).

    Args:
        llm: Cliente resiliente compartido por los tres agentes.
        max_revisions: Tope del ciclo reviewer→synthesizer; el nodo reviewer lo
            usa para marcar `done` cuando ya no habrá más vueltas.
        max_draft_chars: Tope de longitud que el revisor impone al borrador
            (regla determinista; el sintetizador nunca conoce la cifra).

    Returns:
        Mapeo ``nombre_nodo -> función(state) -> patch`` para el StateGraph.
    """
    analyzer = AnalyzerAgent(llm)
    synthesizer = SynthesizerAgent(llm)
    reviewer = ReviewerAgent(llm, max_draft_chars=max_draft_chars)

    def analyzer_node(state: GraphState) -> dict[str, Any]:
        logger.info("Grafo: entrando a 'analyzer'.")
        return analyzer.run(state)

    def synthesizer_node(state: GraphState) -> dict[str, Any]:
        logger.info(
            "Grafo: entrando a 'synthesizer' (%d puntos recibidos).",
            len(state.get("research_points", [])),
        )
        return synthesizer.run(state)

    def reviewer_node(state: GraphState) -> dict[str, Any]:
        logger.info("Grafo: entrando a 'reviewer'.")
        patch = reviewer.run(state)
        # ¿Habrá otra vuelta? Solo si hay revisiones restantes; si no, se cierra
        # aunque el veredicto sea REVISAR (el router forzará END por tope).
        will_loop = bool(patch.get("needs_revision")) and state.get("revision_count", 0) < max_revisions
        if will_loop:
            patch["current_step"] = "awaiting_revision"
            logger.info("Grafo: revisión solicitada, vuelta a 'synthesizer'.")
        else:
            patch["current_step"] = "done"
            logger.info("Grafo: pipeline completado.")
        return patch

    return {"analyzer": analyzer_node, "synthesizer": synthesizer_node, "reviewer": reviewer_node}
