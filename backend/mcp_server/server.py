"""Servidor MCP de finanzas (ejemplo de uso del Model Context Protocol).

Expone 2 tools por stdio para que cualquier cliente MCP (nuestro grafo,
Claude Desktop, MCP Inspector…) las consuma por protocolo:

  - ``get_budget_limit``: lee la "BD ficticia" ``data/budgets.json``.
  - ``get_eur_usd_rate``: tasa EUR→USD en tiempo real (Frankfurter, sin key).

Arranque manual / inspección:
    python -m mcp_server.server        # stdio (lo lanza el grafo solo)
    FINANCE_BUDGETS=data/budgets.json  # override opcional de la BD

Las funciones son importables y puras para poder testearlas sin subprocess.
Las tools NUNCA lanzan: devuelven JSON con los datos o con la clave "error".
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUDGETS = ROOT / "data" / "budgets.json"
FRANKFURTER_URL = os.environ.get(
    "FINANCE_FX_URL", "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD"
)

mcp = FastMCP("finance")


def _budgets_file() -> Path:
    """Ruta de la BD ficticia (override con FINANCE_BUDGETS)."""
    return Path(os.environ.get("FINANCE_BUDGETS", str(DEFAULT_BUDGETS)))


def get_budget_limit_impl(categoria: str) -> str:
    """Devuelve el límite mensual EUR de una categoría como JSON.

    Args:
        categoria: Nombre en mayúsculas (p. ej. "COMIDA").

    Returns:
        JSON con {categoria, limit_eur} o {categoria, limit_eur: null} si no hay.
    """
    try:
        budgets = json.loads(_budgets_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return json.dumps({"categoria": categoria, "limit_eur": None, "error": str(exc)})
    key = (categoria or "").strip().upper()
    limit = budgets.get(key)
    payload: dict[str, object] = {"categoria": key, "limit_eur": limit, "moneda": "EUR"}
    if limit is None:
        payload["note"] = "sin límite definido para esta categoría"
    return json.dumps(payload)


def get_eur_usd_rate_impl() -> str:
    """Devuelve la tasa EUR→USD vigente como JSON (Frankfurter, sin key).

    Returns:
        JSON con {rate, date, source} o {rate: null, error} si la API falla.
        El llamador debe seguir sin conversión y avisarlo en el informe.
    """
    try:
        res = httpx.get(FRANKFURTER_URL, timeout=10.0)
        res.raise_for_status()
        data = res.json()
        rate = float(data["rates"]["USD"])
        return json.dumps(
            {"rate": rate, "date": data.get("date", ""), "source": "frankfurter", "stale": False}
        )
    except Exception as exc:  # noqa: BLE001 — la API externa puede fallar de mil formas
        return json.dumps({"rate": None, "date": "", "source": "frankfurter", "stale": True, "error": str(exc)[:200]})


@mcp.tool()
def get_budget_limit(categoria: str) -> str:
    """Límite mensual de gasto en EUR para una categoría (BD ficticia)."""
    return get_budget_limit_impl(categoria)


@mcp.tool()
def get_eur_usd_rate() -> str:
    """Tipo de cambio EUR→USD en tiempo real (Frankfurter, sin API key)."""
    return get_eur_usd_rate_impl()


if __name__ == "__main__":
    mcp.run()
