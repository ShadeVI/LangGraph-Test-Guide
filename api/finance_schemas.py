"""Esquemas del flujo financiero (contratos validados)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FxInfo(BaseModel):
    """Tasa aplicada en el análisis."""

    rate: float | None = None
    date: str = ""
    source: str = ""
    stale: bool = False


class FinanceResponse(BaseModel):
    """Resultado completo del análisis financiero.

    Attributes:
        filename: Fichero analizado. used_mock: Si fue el ejemplo incorporado.
        mode: "demo" (analista guionizado, MCP real) o "live" (todo real).
        row_count: Filas analizadas. totals: Por categoría y moneda.
        fx_rate/fx_date/fx_source/fx_stale: Tasa aplicada (None si falló).
        budget_alerts: Categorías sobre límite. findings: Hallazgos.
        final_report: Informe Markdown. path/providers_used/errors: trazabilidad.
        tool_iterations: Vueltas analyst↔tools. current_step: Paso final.
    """

    filename: str
    used_mock: bool = False
    mode: str
    kind: str = "finance"
    row_count: int = 0
    totals: dict[str, dict[str, float]] = Field(default_factory=dict)
    fx_rate: float | None = None
    fx_date: str = ""
    fx_source: str = ""
    fx_stale: bool = False
    budget_alerts: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    final_report: str = ""
    path: list[str] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    tool_iterations: int = 0
    current_step: str = "done"
