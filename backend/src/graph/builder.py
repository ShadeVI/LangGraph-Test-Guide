"""Ensamblaje del StateGraph con ciclo de revisión acotado.

Flujo: analyzer → synthesizer → reviewer, con arista CONDICIONAL tras el reviewer:
  - veredicto REVISAR (y revisiones restantes) → vuelta a synthesizer (ciclo);
  - veredicto APROBADO o tope de revisiones → END.

Esto ejercita la capacidad distintiva de LangGraph frente a una cadena lineal:
enrutado dinámico por contenido del estado + ciclo acotado anti-bucle infinito.
"""

from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, StateGraph

from config.logging_config import get_logger
from config.settings import Settings
from src.graph.nodes import make_nodes
from src.llm.factory import build_resilient_client
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

logger = get_logger(__name__)

#: Destinos posibles de la arista condicional tras el reviewer.
ROUTE_TO_SYNTHESIZER = "synthesizer"
ROUTE_TO_END = "end"

#: Nodo de entrada del grafo (lo usa el stream para anunciar quién empieza).
ENTRY_POINT = "analyzer"


def make_router(max_revisions: int) -> Callable[[GraphState], str]:
    """Crea la función de enrutado reviewer → synthesizer|END.

    Args:
        max_revisions: Nº máximo de vueltas reviewer→synthesizer. Garantiza
            terminación aunque el revisor pida revisar eternamente.

    Returns:
        Función `estado -> "synthesizer" | "end"` con logging de la decisión.
    """
    if max_revisions < 0:
        raise ValueError("max_revisions no puede ser negativo.")

    def route_after_reviewer(state: GraphState) -> str:
        """Decide el siguiente nodo según veredicto y contador de revisiones."""
        used = state.get("revision_count", 0)
        if state.get("needs_revision") and used < max_revisions:
            logger.info(
                "Enrutado: reviewer -> synthesizer (revisión %d/%d; motivo: %s).",
                used + 1,
                max_revisions,
                state.get("reviewer_feedback", "sin motivo"),
            )
            return ROUTE_TO_SYNTHESIZER
        if state.get("needs_revision"):
            logger.warning(
                "Enrutado: reviewer -> END (límite de revisiones alcanzado, máx. %d; "
                "se publica el último borrador).",
                max_revisions,
            )
        else:
            logger.info("Enrutado: reviewer -> END (informe aprobado).")
        return ROUTE_TO_END

    return route_after_reviewer


def build_graph_with_llm(
    llm: ResilientLLMClient, max_revisions: int = 2, max_draft_chars: int = 1500
) -> Any:
    """Construye y compila el grafo inyectando el cliente LLM (DIP, testeable).

    Args:
        llm: Cliente resiliente compartido por los tres agentes.
        max_revisions: Vueltas máximas del ciclo reviewer→synthesizer.
        max_draft_chars: Tope que el revisor impone al borrador (el
            sintetizador nunca conoce la cifra).

    Returns:
        Grafo compilado listo para ``.invoke(estado_inicial)``.
    """
    nodes = make_nodes(llm, max_revisions, max_draft_chars)

    builder = StateGraph(GraphState)
    builder.add_node("analyzer", nodes["analyzer"])
    builder.add_node("synthesizer", nodes["synthesizer"])
    builder.add_node("reviewer", nodes["reviewer"])

    builder.set_entry_point(ENTRY_POINT)
    builder.add_edge("analyzer", "synthesizer")
    builder.add_edge("synthesizer", "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        make_router(max_revisions),
        {ROUTE_TO_SYNTHESIZER: "synthesizer", ROUTE_TO_END: END},
    )

    logger.info(
        "Grafo compilado: analyzer -> synthesizer -> reviewer "
        "-[REVISAR]-> synthesizer (máx. %d) / -[APROBADO]-> END.",
        max_revisions,
    )
    return builder.compile()


def build_graph(settings: Settings) -> Any:
    """Construye el grafo con la cadena real de proveedores (Groq→Gemini→Ollama).

    El fallback ocurre *dentro* de cada nodo (cliente resiliente) y el ciclo
    de revisión ocurre *entre* nodos (arista condicional): dos dimensiones
    independientes de resiliencia y control de flujo.

    Args:
        settings: Configuración (modelos, keys, timeouts, max_revisions).

    Returns:
        Grafo compilado listo para ``.invoke(estado_inicial)``.
    """
    return build_graph_with_llm(
        build_resilient_client(settings), settings.max_revisions, settings.max_draft_chars
    )
