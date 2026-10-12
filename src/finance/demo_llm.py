"""Analista guionizado para demo y tests (determinista, sin red ni keys).

Simula dos turnos del loop analyst↔tools: primero pide límites + tasa,
después entrega hallazgos. Los tools que pide existen de verdad en el
servidor MCP, así que la demo ejercita el protocolo completo.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from src.llm.base import LLMStrategy


def _call(name: str, args: dict[str, Any], call_id: str) -> dict[str, Any]:
    """Construye un tool_call con el formato que espera LangChain."""
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


class ScriptedFinanceLLM(LLMStrategy):
    """Doble determinista del analista financiero con tools."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "demo-finance"

    def generate(self, prompt: str) -> str:
        """No usado en el flujo financiero (siempre con tools)."""
        raise NotImplementedError("ScriptedFinanceLLM solo responde con tools.")

    def invoke_with_tools(
        self, messages: list[BaseMessage], tools: list[Any]
    ) -> AIMessage:
        """Turno 1: pide tools. Turno 2+: devuelve hallazgos finales."""
        self.calls += 1
        assert messages, "El historial no debe estar vacío"
        assert tools, "El analista necesita tools enlazadas"
        if self.calls == 1:
            return AIMessage(
                content="Voy a consultar límites de presupuesto y la tasa de cambio.",
                tool_calls=[
                    _call("get_budget_limit", {"categoria": "COMIDA"}, "call_1"),
                    _call("get_budget_limit", {"categoria": "TRANSPORTE"}, "call_2"),
                    _call("get_budget_limit", {"categoria": "OCIO"}, "call_3"),
                    _call("get_eur_usd_rate", {}, "call_4"),
                ],
            )
        return AIMessage(
            content=(
                "- COMIDA supera su límite mensual con 502.00 EUR frente a 300.00 EUR.\n"
                "- OCIO en USD se convierte con la tasa vigente para el total en EUR.\n"
                "- TRANSPORTE se mantiene dentro del límite con 83.50 EUR."
            )
        )
