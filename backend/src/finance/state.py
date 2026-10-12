"""Estado del grafo financiero + errores de entrada (contrato tipado estricto)."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FinanceInputError(ValueError):
    """CSV inválido (columnas, codificación o tamaño): 422 en la API."""


class FinanceState(TypedDict, total=False):
    """Estado que viaja por el grafo financiero.

    El CSV crudo NO viaja entero: `loader` lo parsea y solo guarda filas
    acotadas (máx. MAX_CSV_ROWS) más agregados. `messages` acumula el diálogo
    analista↔tools para auditoría (reducer `add_messages`).

    Attributes:
        filename: Nombre del fichero subido (o del mock).
        used_mock: True si se analizó el CSV de ejemplo.
        csv_text: Contenido CSV en bruto (transitorio, lo consume loader).
        rows: Filas validadas como dicts (acotadas).
        skipped_rows: Filas descartadas por formato.
        row_count: Filas analizadas.
        date_from/date_to: Rango de fechas (texto).
        totals: Totales por categoría y moneda {cat: {"EUR": x, "USD": y}}.
        fx_rate/fx_date/fx_source/fx_stale: Tasa aplicada (None si falló).
        budget_alerts: Alertas "categoría supera límite".
        findings: Hallazgos del analista (viñetas).
        final_report: Informe Markdown del reporter.
        tool_iterations: Vueltas analyst↔tools (acota el loop).
        messages: Historial analista/tools (reducer add_messages).
        path/providers_used/errors/current_step: trazabilidad (igual que GraphState).
    """

    filename: str
    used_mock: bool
    csv_text: str
    rows: list[dict[str, Any]]
    skipped_rows: int
    row_count: int
    date_from: str
    date_to: str
    totals: dict[str, dict[str, float]]
    fx_rate: float | None
    fx_date: str
    fx_source: str
    fx_stale: bool
    budget_alerts: list[str]
    findings: list[str]
    final_report: str
    tool_iterations: int
    messages: Annotated[list[BaseMessage], add_messages]
    path: list[str]
    providers_used: list[str]
    errors: list[str]
    current_step: str


#: Columnas obligatorias del CSV.
REQUIRED_COLUMNS = ("fecha", "concepto", "categoria", "importe", "moneda")

#: Límite de filas y tamaño para no ahogar el estado ni al modelo.
MAX_CSV_ROWS = 500
MAX_CSV_BYTES = 1_000_000


def initial_finance_state(csv_text: str, filename: str, used_mock: bool) -> FinanceState:
    """Crea el estado inicial del grafo financiero.

    Args:
        csv_text: Contenido CSV (del upload o del mock ya leído).
        filename: Nombre a mostrar en el informe.
        used_mock: Si viene del ejemplo incorporado.

    Returns:
        Estado inicial válido para el grafo financiero.
    """
    return FinanceState(
        filename=filename,
        used_mock=used_mock,
        csv_text=csv_text,
        rows=[],
        skipped_rows=0,
        row_count=0,
        date_from="",
        date_to="",
        totals={},
        fx_rate=None,
        fx_date="",
        fx_source="",
        fx_stale=False,
        budget_alerts=[],
        findings=[],
        final_report="",
        tool_iterations=0,
        messages=[],
        path=[],
        providers_used=[],
        errors=[],
        current_step="started",
    )
