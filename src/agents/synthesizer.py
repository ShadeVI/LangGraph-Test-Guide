"""Agente 2 — Sintetizador: sintetiza el borrador técnico (o lo revisa)."""

from __future__ import annotations

from src.agents.base_agent import AgentPatch, BaseAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

SYNTHESIZER_PROMPT = """Eres un sintetizador senior.
Con la consulta y los puntos de investigación, redacta un borrador coherente y técnico.
Es tu redacción Nº {attempt}.

Consulta: "{query}"

Puntos de investigación:
{points}

Observaciones del revisor (vacío si es primera redacción; si hay contenido,
corrige ESOS puntos prioritariamente sin romper el resto):
{feedback}

Reglas:
- Estructura: introducción, desarrollo (uno o varios párrafos por bloque temático) y cierre.
- Tono objetivo y preciso, sin formato Markdown todavía (texto plano).
- Compacto: entre 800 y 1000 caracteres. Nada de relleno, repeticiones ni rodeos.
- No inventes datos fuera de los puntos; si falta información, señálalo.
"""


class SynthesizerAgent(BaseAgent):
    """Sintetiza `research_points` en un borrador en texto plano.

    En reentradas (ciclo revisor→sintetizador) incrementa `revision_count` y usa
    `reviewer_feedback` para corregir el borrador anterior.
    """

    def __init__(self, llm: ResilientLLMClient) -> None:
        super().__init__(llm, "synthesizer")

    def _execute(self, state: GraphState) -> AgentPatch:
        points = "\n".join(f"- {p}" for p in state.get("research_points", []))
        revision_count = state.get("revision_count", 0) + (1 if state.get("draft") else 0)
        feedback = state.get("reviewer_feedback", "") or "(primera redacción)"
        result = self._llm.generate(
            SYNTHESIZER_PROMPT.format(
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
