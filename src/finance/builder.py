"""Ensamblaje del grafo financiero: loader → extractor → analyst ⇄ tools → reporter.

El loop analyst↔tools es la capacidad LangGraph que este flujo demuestra:
el LLM decide qué tools MCP llamar; un router con tope de iteraciones evita
loops infinitos (mismo principio que MAX_REVISIONS del otro grafo).
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from config.logging_config import get_logger
from src.finance.nodes import (
    FinanceAnalystAgent,
    describe_tool_calls,
    extractor_node,
    loader_node,
    reporter_node,
)
from src.finance.state import FinanceState
from src.llm.resilient_client import ResilientLLMClient

logger = get_logger(__name__)

#: Vueltas máximas analyst↔tools (garantiza terminación).
MAX_TOOL_ITERATIONS = 5

ROUTE_TOOLS = "tools"
ROUTE_REPORTER = "reporter"


def make_finance_router(max_tool_iters: int = MAX_TOOL_ITERATIONS, log: bool = True) -> Callable[[FinanceState], str]:
    """Crea el enrutado analyst → tools|reporter.

    Args:
        max_tool_iters: Vueltas máximas del loop de tools.
        log: False cuando solo se narra (streaming) para no duplicar el log
            que ya emite el router real al ejecutar la arista.

    Returns:
        Función `estado -> "tools" | "reporter"` con logging de la decisión.
    """
    if max_tool_iters < 0:
        raise ValueError("max_tool_iters no puede ser negativo.")

    def route_after_analyst(state: FinanceState) -> str:
        """Si el analista pidió tools (y quedan vueltas), a tools; si no, a reporter."""
        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        wants_tools = isinstance(last, AIMessage) and bool(last.tool_calls)
        used = state.get("tool_iterations", 0)
        if wants_tools and used < max_tool_iters:
            if log:
                logger.info("Enrutado finance: analyst -> tools (vuelta %d/%d).", used + 1, max_tool_iters)
            return ROUTE_TOOLS
        if wants_tools:
            if log:
                logger.warning(
                    "Enrutado finance: analyst -> reporter (tope de %d iteraciones; se informa sin más tools).",
                    max_tool_iters,
                )
        elif log:
            logger.info("Enrutado finance: analyst -> reporter (sin tool_calls).")
        return ROUTE_REPORTER

    return route_after_analyst


def build_finance_graph(
    llm: ResilientLLMClient, tools: list[Any], max_tool_iters: int = MAX_TOOL_ITERATIONS
) -> Any:
    """Construye y compila el grafo financiero (DIP: LLM y tools inyectados).

    Args:
        llm: Cliente resiliente para el analista.
        tools: Tools LangChain (del servidor MCP o dobles en tests).
        max_tool_iters: Tope del loop analyst↔tools.

    Returns:
        Grafo compilado (usar ``ainvoke``: hay tools async).
    """
    analyst = FinanceAnalystAgent(llm, tools)
    executor = ToolNode(tools)

    def analyst_node(state: FinanceState) -> dict[str, Any]:
        logger.info("Grafo finance: entrando a 'analyst'.")
        return analyst.run(state)

    async def tools_node(state: FinanceState) -> dict[str, Any]:
        logger.info(
            "Grafo finance: ejecutando tools: %s.", describe_tool_calls(_pending_tool_calls(state))
        )
        # Async a propósito: las tools MCP solo viven en modo async.
        # El grafo finance se ejecuta con `ainvoke` (los nodos sync corren en hilos).
        out = await executor.ainvoke(state)
        used = state.get("tool_iterations", 0) + 1
        return {
            "messages": out["messages"],
            "tool_iterations": used,
            "current_step": "tools",
            "path": [*state.get("path", []), "tools"],
        }

    builder = StateGraph(FinanceState)
    builder.add_node("loader", loader_node)
    builder.add_node("extractor", extractor_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("tools", tools_node)
    builder.add_node("reporter", reporter_node)

    builder.set_entry_point("loader")
    builder.add_edge("loader", "extractor")
    builder.add_edge("extractor", "analyst")
    builder.add_conditional_edges(
        "analyst",
        make_finance_router(max_tool_iters),
        {ROUTE_TOOLS: "tools", ROUTE_REPORTER: "reporter"},
    )
    builder.add_edge("tools", "analyst")
    builder.add_edge("reporter", END)

    logger.info("Grafo finance compilado (máx. %d iteraciones de tools).", max_tool_iters)
    return builder.compile()


def _pending_tool_calls(state: FinanceState) -> list[dict[str, Any]]:
    """Tool_calls pendientes en el último mensaje del analista."""
    messages = state.get("messages", [])
    last = messages[-1] if messages else None
    if isinstance(last, AIMessage):
        return list(last.tool_calls or [])
    return []
