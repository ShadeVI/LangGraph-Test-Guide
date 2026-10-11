"""LLM guionizado para el modo demo de la API (determinista, sin red ni keys).

Flujo fijo para que la demo siempre muestre lo interesante: el ciclo
editor→writer (REVISAR una vez) y luego APROBADO.
"""

from __future__ import annotations

from src.llm.base import LLMStrategy


class ScriptedDemoLLM(LLMStrategy):
    """Responde por rol detectando el agente en el prompt (ver demo_paths.py)."""

    def __init__(self) -> None:
        self._research = (
            "- LangGraph orquesta agentes como un grafo de estados\n"
            "- Cada nodo lee el estado y devuelve un patch parcial\n"
            "- Las aristas condicionales permiten ciclos y reintentos"
        )
        self._writers = [
            "Borrador inicial incompleto.",
            "Borrador corregido con grafos, estado y aristas condicionales.",
        ]
        self._editors = [
            "VEREDICTO: REVISAR - falta explicar las aristas condicionales\n\n# Parcial",
            "VEREDICTO: APROBADO\n\n# Informe demo\n\n## Definición\nTexto final de demostración.",
        ]
        self._w = 0
        self._e = 0

    @property
    def name(self) -> str:
        return "demo"

    def generate(self, prompt: str) -> str:
        """Sirve la siguiente réplica del guion según el agente que llama."""
        if "analista de investigación" in prompt:
            return self._research
        if "redactor técnico" in prompt:
            out = self._writers[min(self._w, len(self._writers) - 1)]
            self._w += 1
            return out
        out = self._editors[min(self._e, len(self._editors) - 1)]
        self._e += 1
        return out


def build_demo_client() -> "ResilientLLMClient":
    """Crea el cliente resiliente con el LLM guionizado (un solo proveedor)."""
    from src.llm.resilient_client import ResilientLLMClient

    return ResilientLLMClient([ScriptedDemoLLM()])
