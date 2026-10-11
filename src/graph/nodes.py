"""Adaptadores nodo-grafo: funciones puras que LangGraph puede orquestar."""

from __future__ import annotations

from typing import Any

from config.logging_config import get_logger
from src.agents.editor import EditorAgent
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

logger = get_logger(__name__)


def make_nodes(llm: ResilientLLMClient, max_revisions: int = 2) -> dict[str, Any]:
    """Crea las funciones de nodo con sus agentes inyectados (SRP + DIP).

    Args:
        llm: Cliente resiliente compartido por los tres agentes.
        max_revisions: Tope del ciclo editor→writer; el nodo editor lo usa
            para marcar `done` cuando ya no habrá más vueltas.

    Returns:
        Mapeo ``nombre_nodo -> función(state) -> patch`` para el StateGraph.
    """
    researcher = ResearcherAgent(llm)
    writer = WriterAgent(llm)
    editor = EditorAgent(llm)

    def researcher_node(state: GraphState) -> dict[str, Any]:
        logger.info("Grafo: entrando a 'researcher'.")
        return researcher.run(state)

    def writer_node(state: GraphState) -> dict[str, Any]:
        logger.info(
            "Grafo: entrando a 'writer' (%d puntos recibidos).",
            len(state.get("research_points", [])),
        )
        return writer.run(state)

    def editor_node(state: GraphState) -> dict[str, Any]:
        logger.info("Grafo: entrando a 'editor'.")
        patch = editor.run(state)
        # ¿Habrá otra vuelta? Solo si hay revisiones restantes; si no, se cierra
        # aunque el veredicto sea REVISAR (el router forzará END por tope).
        will_loop = bool(patch.get("needs_revision")) and state.get("revision_count", 0) < max_revisions
        if will_loop:
            patch["current_step"] = "awaiting_revision"
            logger.info("Grafo: revisión solicitada, vuelta a 'writer'.")
        else:
            patch["current_step"] = "done"
            logger.info("Grafo: pipeline completado.")
        return patch

    return {"researcher": researcher_node, "writer": writer_node, "editor": editor_node}
