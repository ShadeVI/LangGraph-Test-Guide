"""Nodos del grafo financiero: loader, extractor, analyst, reporter y router.

loader/extractor/reporter son deterministas (sin LLM: rápidos y testeables);
solo analyst llama al modelo, con tools MCP enlazadas (loop acotado).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from config.logging_config import get_logger
from src.agents.base_agent import AgentPatch, BaseAgent
from src.finance.state import (
    MAX_CSV_ROWS,
    REQUIRED_COLUMNS,
    FinanceInputError,
    FinanceState,
)
from src.llm.resilient_client import ResilientLLMClient

logger = get_logger(__name__)
MOCK_FILE = Path(__file__).resolve().parents[2] / "data" / "mock_gastos.csv"

ANALYST_SYSTEM = """Eres un analista financiero senior. Tienes tools MCP:
- get_budget_limit(categoria): límite mensual EUR (BD ficticia).
- get_eur_usd_rate(): tasa EUR→USD vigente (sin argumentos).

Procedimiento obligatorio:
1. Pide el límite de las 3 categorías con mayor gasto en EUR.
2. Si hay importes en USD, pide la tasa UNA vez.
3. Termina con 3-6 hallazgos en viñetas ("- ...") con cifras concretas.
Si una tool falla, continúa sin ella y dilo en los hallazgos."""


def _parse_amount(raw: str) -> float | None:
    """Parsea importes con punto o coma decimal. None si inválido."""
    text = (raw or "").strip()
    for candidate in (text, text.replace(",", ".")):
        try:
            return float(candidate)
        except ValueError:
            continue
    return None


def loader_node(state: FinanceState) -> dict[str, Any]:
    """Valida y parsea el CSV (o el mock): filas acotadas + mensaje inicial."""
    logger.info("Grafo finance: entrando a 'loader'.")
    csv_text = (state.get("csv_text") or "").strip()
    used_mock = False
    filename = state.get("filename") or "gastos.csv"
    if not csv_text:
        csv_text = MOCK_FILE.read_text(encoding="utf-8-sig")
        used_mock = True
        filename = MOCK_FILE.name
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
    except csv.Error as exc:
        raise FinanceInputError(f"CSV ilegible: {exc}") from exc
    if reader.fieldnames is None or set(REQUIRED_COLUMNS) - set(reader.fieldnames):
        raise FinanceInputError(
            f"Columnas requeridas: {', '.join(REQUIRED_COLUMNS)} (hay: {reader.fieldnames})"
        )
    rows: list[dict[str, Any]] = []
    skipped = 0
    total_read = 0
    for record in reader:
        total_read += 1
        if len(rows) >= MAX_CSV_ROWS:
            skipped += 1
            continue
        amount = _parse_amount(str(record.get("importe", "")))
        currency = str(record.get("moneda", "")).strip().upper()
        category = str(record.get("categoria", "")).strip().upper()
        if amount is None or currency not in ("EUR", "USD") or not category:
            skipped += 1
            continue
        rows.append(
            {
                "fecha": str(record.get("fecha", "")).strip(),
                "concepto": str(record.get("concepto", "")).strip(),
                "categoria": category,
                "importe": amount,
                "moneda": currency,
            }
        )
    if not rows:
        raise FinanceInputError("El CSV no contiene filas válidas.")
    dates = sorted(r["fecha"] for r in rows if r["fecha"])
    logger.info("Loader: %d filas válidas (%d descartadas), mock=%s.", len(rows), skipped, used_mock)
    summary = (
        f"Fichero {filename}: {len(rows)} movimientos"
        f" ({dates[0]} a {dates[-1]})" if dates else f"Fichero {filename}: {len(rows)} movimientos"
    )
    return {
        "filename": filename,
        "used_mock": used_mock,
        "rows": rows,
        "skipped_rows": skipped,
        "row_count": len(rows),
        "date_from": dates[0] if dates else "",
        "date_to": dates[-1] if dates else "",
        "messages": [HumanMessage(content=summary)],
        "current_step": "loader",
        "path": [*state.get("path", []), "loader"],
    }


def extractor_node(state: FinanceState) -> dict[str, Any]:
    """Agrega totales por categoría y moneda (determinista, sin LLM)."""
    logger.info("Grafo finance: entrando a 'extractor'.")
    totals: dict[str, dict[str, float]] = {}
    for row in state.get("rows", []):
        bucket = totals.setdefault(row["categoria"], {"EUR": 0.0, "USD": 0.0})
        bucket[row["moneda"]] += row["importe"]
    top = sorted(totals, key=lambda c: totals[c]["EUR"], reverse=True)[:3]
    logger.info("Extractor: %d categorías, top=%s.", len(totals), top)
    return {
        "totals": totals,
        "messages": [HumanMessage(content=f"Totales por categoría: {json.dumps(totals)}")],
        "current_step": "extractor",
        "path": [*state.get("path", []), "extractor"],
    }


class FinanceAnalystAgent(BaseAgent):
    """Analista con tools MCP: decide qué consultar y redacta hallazgos.

    Args:
        llm: Cliente resiliente (con fallback entre proveedores).
        tools: Tools LangChain del servidor MCP ya enlazables.
    """

    def __init__(self, llm: ResilientLLMClient, tools: list[Any]) -> None:
        super().__init__(llm, "analyst")
        self._tools = tools

    def _execute(self, state: FinanceState) -> AgentPatch:
        totals = json.dumps(state.get("totals", {}))
        tool_names = ", ".join(t.name for t in self._tools)
        messages = [
            SystemMessage(content=ANALYST_SYSTEM + f"\nTools disponibles: {tool_names}."),
            HumanMessage(content=f"Analiza estos gastos: {totals}"),
            *(m for m in state.get("messages", []) if isinstance(m, (AIMessage, ToolMessage))),
        ]
        result = self._llm.generate_with_tools(messages, self._tools)
        self._logger.info(
            "Analista pide herramientas: %s (vía %s).",
            describe_tool_calls(result.message.tool_calls),
            result.provider,
        )
        return {
            "messages": [result.message],
            "_providers_used": [result.provider],
            "_errors": list(result.failures),
        }


def describe_tool_calls(tool_calls: list[dict[str, Any]] | None) -> str:
    """Resume tool_calls como 'get_budget_limit ×3, get_eur_usd_rate'.

    Args:
        tool_calls: Lista de tool_call dicts (con clave "name").

    Returns:
        Resumen agrupado, o "ninguna" si está vacío.
    """
    names = [str(c.get("name", "?")) for c in tool_calls or []]
    if not names:
        return "ninguna"
    counts: dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    return ", ".join(f"{name} ×{total}" if total > 1 else name for name, total in counts.items())


def _read_tool_json(messages: list[Any], tool_name: str) -> list[dict[str, Any]]:
    """Extrae los JSON devueltos por una tool de los ToolMessages."""
    found = []
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == tool_name:
            try:
                found.append(json.loads(str(message.content)))
            except (json.JSONDecodeError, TypeError):
                continue
    return found


def reporter_node(state: FinanceState) -> dict[str, Any]:
    """Compone el informe Markdown (determinista, a partir de datos + hallazgos)."""
    logger.info("Grafo finance: entrando a 'reporter'.")
    totals = state.get("totals", {})
    fx_docs = _read_tool_json(state.get("messages", []), "get_eur_usd_rate")
    fx = fx_docs[-1] if fx_docs else {}
    rate = fx.get("rate")
    limits = {d["categoria"]: d.get("limit_eur") for d in _read_tool_json(state.get("messages", []), "get_budget_limit")}

    alerts: list[str] = []
    lines = ["| Categoría | EUR | USD | Total EUR |", "|---|---|---|---|"]
    grand = 0.0
    for category in sorted(totals):
        eur = totals[category].get("EUR", 0.0)
        usd = totals[category].get("USD", 0.0)
        converted = usd / rate if (rate and usd) else 0.0
        total_eur = eur + converted
        grand += total_eur
        usd_cell = f"{usd:.2f} (~{converted:.2f} EUR)" if usd else "—"
        if rate is None and usd:
            usd_cell = f"{usd:.2f} (sin convertir: tasa no disponible)"
        lines.append(f"| {category} | {eur:.2f} | {usd_cell} | {total_eur:.2f} |")
        limit = limits.get(category)
        if limit is not None and total_eur > limit:
            alerts.append(f"⚠ {category}: gasto {total_eur:.2f} EUR supera el límite {limit:.2f} EUR")

    if rate:
        fx_line = f"Tasa EUR→USD **{rate}** del {fx.get('date', '?')} (fuente: {fx.get('source', '?')})."
    else:
        fx_line = "Tasa no disponible (la API falló): los importes USD se muestran sin convertir."
        alerts.append("⚠ Sin tasa de cambio: totales en USD sin convertir a EUR.")

    last_ai = next(
        (m.content for m in reversed(state.get("messages", [])) if isinstance(m, AIMessage) and m.content),
        "",
    )
    bullets = [ln.strip()[2:].strip() for ln in str(last_ai).splitlines() if ln.strip().startswith("- ")]
    findings = bullets or ([str(last_ai).strip()] if str(last_ai).strip() else ["Sin hallazgos."])

    mock_note = " (datos de ejemplo)" if state.get("used_mock") else ""
    alert_lines = [f"- {a}" for a in alerts] or ["- Sin alertas: todo dentro de límites conocidos."]
    report = "\n".join(
        [
            f"# Informe de gastos — {state.get('filename', '')}{mock_note}",
            "",
            f"**Filas analizadas:** {state.get('row_count', 0)} "
            f"({state.get('date_from', '?')} a {state.get('date_to', '?')}) · "
            f"**Descartadas:** {state.get('skipped_rows', 0)}",
            "",
            "## Totales por categoría (EUR)",
            "",
            *lines,
            "",
            f"**Total general:** {grand:.2f} EUR",
            "",
            "## Presupuesto",
            "",
            *alert_lines,
            "",
            "## Tipo de cambio",
            "",
            fx_line,
            "",
            "## Hallazgos del analista",
            "",
            *(f"- {f}" for f in findings),
            "",
            f"_Generado por grafo multi-agente · revisiones de tools: {state.get('tool_iterations', 0)}_",
        ]
    )
    logger.info("Reporter: informe de %d caracteres, %d alertas.", len(report), len(alerts))
    return {
        "fx_rate": rate,
        "fx_date": str(fx.get("date", "")),
        "fx_source": str(fx.get("source", "")),
        "fx_stale": bool(fx.get("stale", False)),
        "budget_alerts": alerts,
        "findings": findings,
        "final_report": report,
        "current_step": "done",
        "path": [*state.get("path", []), "reporter"],
    }
