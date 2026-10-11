"""Demuestra las rutas NO lineales del grafo con 3 inputs de ejemplo.

Cada escenario usa un LLM guionizado (sin red ni API keys) que simula cómo
responderían los proveedores a cada input, evidenciando:

  A. Ruta lineal:   researcher → writer → editor → END (veredicto APROBADO).
  B. Ciclo real:    researcher → writer → editor → writer → editor → END
     (veredicto REVISAR una vez; el feedback guía la reescritura).
  C. Fallback+tope: el 1er proveedor falla en writer (fallback a 2º) y el
     editor pide revisar 2 veces con MAX=1 → END forzado con aviso.

Ejecutar:  python demo_paths.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.logging_config import configure_logging, get_logger
from src.graph.builder import build_graph_with_llm
from src.llm.base import LLMProviderError, LLMStrategy
from src.llm.resilient_client import ResilientLLMClient
from src.state import initial_state

logger = get_logger(__name__)


class ScriptedLLM(LLMStrategy):
    """Sirve réplicas guionizadas según el agente que llama (por su prompt)."""

    def __init__(
        self,
        research: str,
        writers: list[str],
        editors: list[str],
    ) -> None:
        self._research = research
        self._writers = writers
        self._editors = editors
        self._w = 0
        self._e = 0

    @property
    def name(self) -> str:
        return "guion"

    def generate(self, prompt: str) -> str:
        if "analista de investigación" in prompt:
            return self._research
        if "redactor técnico" in prompt:
            out = self._writers[min(self._w, len(self._writers) - 1)]
            self._w += 1
            return out
        out = self._editors[min(self._e, len(self._editors) - 1)]
        self._e += 1
        return out


class FlakyFirstLLM(LLMStrategy):
    """Falla SOLO en la primera llamada (simula 429 en Groq) y luego delega."""

    def __init__(self, fallback: LLMStrategy) -> None:
        self._fallback = fallback
        self._calls = 0

    @property
    def name(self) -> str:
        return "groq-simulado"

    def generate(self, prompt: str) -> str:
        self._calls += 1
        if self._calls == 1:
            raise LLMProviderError("429 rate limit superado (simulado)")
        return self._fallback.generate(prompt)


def run_scenario(title: str, query: str, strategies: list[LLMStrategy], max_revisions: int) -> None:
    """Ejecuta un escenario y resume ruta, proveedores, errores e informe."""
    print("\n" + "=" * 72)
    print(f"ESCENARIO {title}")
    print(f"INPUT: {query!r}   (MAX_REVISIONS={max_revisions})")
    print("=" * 72)
    graph = build_graph_with_llm(ResilientLLMClient(strategies), max_revisions)
    final = graph.invoke(initial_state(query))
    print("-" * 72)
    print(f"RUTA:        {' -> '.join(final['path'])}")
    print(f"REVISIONES:  {final['revision_count']}")
    print(f"PROVEEDORES: {final['providers_used']}")
    print(f"ERRORES:     {final['errors'] or 'ninguno'}")
    print(f"STEP FINAL:  {final['current_step']}")
    print(f"INFORME:\n{final['final_report'][:400]}")


def main() -> None:
    configure_logging("INFO")

    # A · El editor aprueba a la primera: ruta lineal.
    run_scenario(
        "A · aprobación directa (ruta lineal)",
        "¿Qué es LangGraph y para qué sirve?",
        [
            ScriptedLLM(
                research="- LangGraph modela flujos como grafos\n- El estado viaja entre nodos",
                writers=["Borrador completo sobre LangGraph."],
                editors=["VEREDICTO: APROBADO\n\n# ¿Qué es LangGraph?\n\nTexto final."],
            )
        ],
        max_revisions=2,
    )

    # B · El editor pide una revisión: ciclo editor→writer→editor.
    run_scenario(
        "B · una revisión (ciclo editor→writer)",
        "Explica la fotosíntesis de forma técnica",
        [
            ScriptedLLM(
                research="- Fase luminosa\n- Ciclo de Calvin",
                writers=["Borrador flojo.", "Borrador corregido con ambas fases."],
                editors=[
                    "VEREDICTO: REVISAR - falta el ciclo de Calvin\n\n# Parcial",
                    "VEREDICTO: APROBADO\n\n# Fotosíntesis\n\nTexto final completo.",
                ],
            )
        ],
        max_revisions=2,
    )

    # C · Fallo de proveedor + revisiones eternas con tope MAX=1.
    scripted_c = ScriptedLLM(
        research="- Strategy define familia de algoritmos\n- Factory crea objetos",
        writers=["Borrador v1.", "Borrador v2."],
        editors=["VEREDICTO: REVISAR - siempre se puede mejorar\n\n# Parcial v1"],
    )
    run_scenario(
        "C · fallback 429 + tope de revisiones (END forzado)",
        "Compara Strategy vs Factory con ejemplos",
        [FlakyFirstLLM(scripted_c), scripted_c],
        max_revisions=1,
    )


if __name__ == "__main__":
    main()
