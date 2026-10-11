"""Agente 1 — Investigador: extrae puntos clave estructurados."""

from __future__ import annotations

from src.agents.base_agent import AgentPatch, BaseAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

RESEARCHER_PROMPT = """Eres un analista de investigación senior.
Analiza la siguiente consulta y extrae entre 5 y 8 puntos clave estructurados.

Consulta: "{query}"

Reglas:
- Cada punto en una línea separada empezando con "- ".
- Hechos, definiciones, causas, consecuencias y preguntas abiertas relevantes.
- Sin introducciones ni conclusiones: SOLO la lista de puntos.
"""


class ResearcherAgent(BaseAgent):
    """Convierte la consulta en una lista de puntos clave accionables."""

    def __init__(self, llm: ResilientLLMClient) -> None:
        super().__init__(llm, "researcher")

    def _execute(self, state: GraphState) -> AgentPatch:
        query = state["query"]
        result = self._llm.generate(RESEARCHER_PROMPT.format(query=query))
        points = [ln.strip()[2:].strip() for ln in result.text.splitlines() if ln.strip().startswith("- ")]
        if not points:  # Respaldo: respuesta no lista → bloque único.
            points = [result.text.strip()]
        self._logger.info("Extraídos %d puntos clave.", len(points))
        return {
            "research_points": points,
            "_providers_used": [result.provider],
            "_errors": list(result.failures),
        }
