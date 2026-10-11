"""Agente 2 — Redactor: sintetiza el borrador técnico (o lo revisa)."""

from __future__ import annotations

from src.agents.base_agent import AgentPatch, BaseAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

WRITER_PROMPT = """Eres un redactor técnico senior.
Con la consulta y los puntos de investigación, redacta un borrador coherente y técnico.
Es tu redacción Nº {attempt}.

Consulta: "{query}"

Puntos de investigación:
{points}

Observaciones del editor (vacío si es primera redacción; si hay contenido,
corrige ESOS puntos prioritariamente sin romper el resto):
{feedback}

Reglas:
- Estructura: introducción, desarrollo (uno o varios párrafos por bloque temático) y cierre.
- Tono objetivo y preciso, sin formato Markdown todavía (texto plano).
- No inventes datos fuera de los puntos; si falta información, señálalo.
"""


class WriterAgent(BaseAgent):
    """Sintetiza `research_points` en un borrador en texto plano.

    En reentradas (ciclo editor→writer) incrementa `revision_count` y usa
    `editor_feedback` para corregir el borrador anterior.
    """

    def __init__(self, llm: ResilientLLMClient) -> None:
        super().__init__(llm, "writer")

    def _execute(self, state: GraphState) -> AgentPatch:
        points = "\n".join(f"- {p}" for p in state.get("research_points", []))
        revision_count = state.get("revision_count", 0) + (1 if state.get("draft") else 0)
        feedback = state.get("editor_feedback", "") or "(primera redacción)"
        result = self._llm.generate(
            WRITER_PROMPT.format(
                query=state["query"],
                points=points,
                feedback=feedback,
                attempt=revision_count + 1,
            )
        )
        draft = result.text.strip()
        self._logger.info(
            "Borrador Nº %d de %d caracteres (%d puntos base).",
            revision_count + 1,
            len(draft),
            len(state.get("research_points", [])),
        )
        return {
            "draft": draft,
            "revision_count": revision_count,
            "_providers_used": [result.provider],
            "_errors": list(result.failures),
        }
