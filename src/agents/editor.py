"""Agente 3 — Editor: pule estilo, emite veredicto y aplica Markdown profesional."""

from __future__ import annotations

from config.logging_config import get_logger
from src.agents.base_agent import AgentPatch, BaseAgent
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

logger = get_logger(__name__)

EDITOR_PROMPT = """Eres un editor profesional y exigente.
Evalúa el borrador frente a los puntos de investigación y responde en DOS partes:

1. PRIMERA LÍNEA (obligatoria, formato exacto): el veredicto.
   - "VEREDICTO: APROBADO" si cubre los puntos con calidad suficiente.
   - "VEREDICTO: REVISAR - <motivo breve>" si faltan puntos, hay errores graves
     o es demasiado superficial. El motivo guiará la reescritura.
2. Tras una línea en blanco, el documento Markdown pulido
   (título `# ` de la consulta "{query}", secciones `## `, listas y negritas).

Puntos de investigación:
{points}

Borrador (revisión Nº {attempt}):
---
{draft}
---
"""

VERDICT_PREFIX = "VEREDICTO:"


class EditorAgent(BaseAgent):
    """Convierte el `draft` en `final_report` o pide revisión (`needs_revision`).

    El veredicto alimenta la arista condicional del grafo: REVISAR reencamina
    a `writer` hasta agotar `MAX_REVISIONS`; APROBADO lleva a END.
    """

    def __init__(self, llm: ResilientLLMClient) -> None:
        super().__init__(llm, "editor")

    def _execute(self, state: GraphState) -> AgentPatch:
        points = "\n".join(f"- {p}" for p in state.get("research_points", []))
        result = self._llm.generate(
            EDITOR_PROMPT.format(
                query=state["query"],
                points=points,
                draft=state.get("draft", ""),
                attempt=state.get("revision_count", 0) + 1,
            )
        )
        needs_revision, feedback, body = self._parse_verdict(result.text)
        if needs_revision:
            self._logger.info("Veredicto: REVISAR (motivo: %s).", feedback)
        else:
            self._logger.info("Veredicto: APROBADO (%d caracteres finales).", len(body))
        return {
            # Siempre se conserva el cuerpo: si el ciclo agota MAX_REVISIONS,
            # el enrutador fuerza END y se publica esta última versión.
            "final_report": body,
            "needs_revision": needs_revision,
            "editor_feedback": feedback,
            "_providers_used": [result.provider],
            "_errors": list(result.failures),
        }

    @staticmethod
    def _parse_verdict(raw: str) -> tuple[bool, str, str]:
        """Extrae (necesita_revision, motivo, cuerpo_markdown) de la respuesta.

        Args:
            raw: Respuesta completa del LLM (1ª línea = veredicto).

        Returns:
            Tupla con el veredicto parseado. Sin línea de veredicto se aprueba
            con aviso (fail-open) para no bloquear el pipeline por formato.
        """
        text = raw.strip()
        lines = text.splitlines()
        if not lines or not lines[0].strip().upper().startswith(VERDICT_PREFIX):
            logger.warning("Editor sin línea de veredicto; se aprueba por defecto.")
            return False, "", text
        first = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
        if first.upper().startswith("REVISAR"):
            feedback = first[7:].strip(" -:") or "Sin motivo detallado."
            return True, feedback, body
        return False, "", body
