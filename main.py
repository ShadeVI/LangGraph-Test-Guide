"""Punto de entrada CLI de la aplicación multi-agente.

Uso:
    python main.py --query "¿Qué es LangGraph?"
    python main.py --query "..." --output output/informe.md
    python main.py  (modo interactivo)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from config.logging_config import configure_logging, get_logger
from config.settings import get_settings
from src.graph.builder import build_graph
from src.state import GraphState, initial_state

logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parsea argumentos CLI.

    Args:
        argv: Argumentos (``None`` = ``sys.argv``).

    Returns:
        Namespace con ``query`` y ``output``.
    """
    parser = argparse.ArgumentParser(description="Pipeline multi-agente: investiga, redacta y edita.")
    parser.add_argument("--query", "-q", type=str, default="", help="Consulta a procesar.")
    parser.add_argument("--output", "-o", type=str, default="", help="Ruta del Markdown final.")
    return parser.parse_args(argv)


def run_pipeline(query: str) -> GraphState:
    """Ejecuta el grafo completo para una consulta.

    Args:
        query: Consulta del usuario.

    Returns:
        Estado final con `final_report`, `providers_used` y `errors`.

    Raises:
        ValueError: Si la consulta está vacía.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("=== Inicio del pipeline multi-agente ===")
    logger.info("Cadena de fallback: Groq -> Gemini -> Ollama local.")

    graph = build_graph(settings)
    final_state: GraphState = graph.invoke(initial_state(query))

    logger.info("=== Pipeline finalizado (step=%s) ===", final_state.get("current_step"))
    logger.info("Ruta recorrida: %s", " -> ".join(final_state.get("path", [])))
    logger.info(
        "Revisiones: %d | Proveedores usados: %s",
        final_state.get("revision_count", 0),
        final_state.get("providers_used"),
    )
    if final_state.get("errors"):
        logger.warning("Fallos recuperados vía fallback: %d", len(final_state["errors"]))
        for err in final_state["errors"]:
            logger.warning("  ↳ %s", err)
    return final_state


def main(argv: list[str] | None = None) -> int:
    """CLI principal: resuelve query, ejecuta pipeline, muestra/guarda informe."""
    load_dotenv()
    args = parse_args(argv)
    query = args.query.strip() or input("Introduce tu consulta: ").strip()
    if not query:
        logger.error("Consulta vacía; nada que procesar.")
        return 2
    try:
        final = run_pipeline(query)
    except Exception as exc:  # noqa: BLE001 — el CLI debe reportar, no trazar
        logger.error("Pipeline abortado: %s", exc)
        return 1

    report = final.get("final_report", "")
    print("\n" + "=" * 70 + "\nINFORME FINAL\n" + "=" * 70 + "\n")
    print(report)
    print("\n" + "=" * 70)
    logger.info("Proveedores: %s | Puntos: %d", final.get("providers_used"), len(final.get("research_points", [])))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        logger.info("Informe guardado en: %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
