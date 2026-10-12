"""Tests del flujo financiero (dobles + MCP real local, sin API keys).

Ejecutar:  python tests/test_finance.py
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.tools import StructuredTool  # noqa: E402

from config.logging_config import configure_logging  # noqa: E402
from src.finance.builder import (  # noqa: E402
    MAX_TOOL_ITERATIONS,
    build_finance_graph,
    make_finance_router,
)
from src.finance.demo_llm import ScriptedFinanceLLM  # noqa: E402
from src.finance.nodes import extractor_node, loader_node, reporter_node  # noqa: E402
from src.finance.state import FinanceInputError, initial_finance_state  # noqa: E402
from src.llm.resilient_client import ResilientLLMClient  # noqa: E402

configure_logging("ERROR")

MOCK_CSV = (ROOT / "data" / "mock_gastos.csv").read_text(encoding="utf-8")


def _fake_tools() -> list[StructuredTool]:
    """Dobles sync de las tools MCP (sin subprocess, sin red)."""
    import json

    def budget(categoria: str) -> str:
        limits = {"COMIDA": 300.0, "TRANSPORTE": 120.0, "OCIO": 150.0}
        return json.dumps({"categoria": categoria, "limit_eur": limits.get(categoria)})

    def fx() -> str:
        return json.dumps({"rate": 1.10, "date": "2026-10-09", "source": "fake", "stale": False})

    return [
        StructuredTool.from_function(func=budget, name="get_budget_limit", description="Límite mensual EUR."),
        StructuredTool.from_function(func=fx, name="get_eur_usd_rate", description="Tasa EUR->USD."),
    ]


class TestLoaderExtractor(unittest.TestCase):
    def test_loader_sin_csv_usa_mock(self) -> None:
        patch = loader_node(initial_finance_state("", "nada.csv", False))
        self.assertTrue(patch["used_mock"])
        self.assertEqual(patch["filename"], "mock_gastos.csv")
        self.assertEqual(patch["row_count"], 12)

    def test_loader_rechaza_columnas(self) -> None:
        with self.assertRaises(FinanceInputError):
            loader_node(initial_finance_state("a,b\n1,2", "mal.csv", False))

    def test_loader_descarta_filas_malas(self) -> None:
        csv = "fecha,concepto,categoria,importe,moneda\n2026-01-01,X,COMIDA,no-numero,EUR\n2026-01-02,Y,COMIDA,10,EUR\n"
        patch = loader_node(initial_finance_state(csv, "ok.csv", False))
        self.assertEqual(patch["row_count"], 1)
        self.assertEqual(patch["skipped_rows"], 1)

    def test_extractor_totales_por_moneda(self) -> None:
        state = initial_finance_state("", "", False)
        state.update(loader_node(initial_finance_state(MOCK_CSV, "mock.csv", False)))
        patch = extractor_node(state)
        self.assertAlmostEqual(patch["totals"]["COMIDA"]["EUR"], 502.00)
        self.assertAlmostEqual(patch["totals"]["OCIO"]["USD"], 239.99)
        self.assertAlmostEqual(patch["totals"]["TRANSPORTE"]["EUR"], 83.50)


class TestRouter(unittest.TestCase):
    def test_con_tool_calls_va_a_tools(self) -> None:
        route = make_finance_router(5)({"messages": [AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1", "type": "tool_call"}])], "tool_iterations": 0})
        self.assertEqual(route, "tools")

    def test_en_tope_fuerza_reporter(self) -> None:
        route = make_finance_router(1)({"messages": [AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1", "type": "tool_call"}])], "tool_iterations": 1})
        self.assertEqual(route, "reporter")

    def test_sin_calls_va_a_reporter(self) -> None:
        route = make_finance_router(5)({"messages": [HumanMessage(content="hola")], "tool_iterations": 0})
        self.assertEqual(route, "reporter")


class TestFullGraph(unittest.TestCase):
    def test_loop_tools_y_alerta_comida(self) -> None:
        """loader→extractor→analyst→tools→analyst→reporter con dobles sync."""
        llm = ResilientLLMClient([ScriptedFinanceLLM()])
        graph = build_finance_graph(llm, _fake_tools(), max_tool_iters=MAX_TOOL_ITERATIONS)
        final = asyncio.run(graph.ainvoke(initial_finance_state(MOCK_CSV, "mock.csv", False)))
        self.assertEqual(
            final["path"],
            ["loader", "extractor", "analyst", "tools", "analyst", "reporter"],
        )
        self.assertEqual(final["tool_iterations"], 1)
        self.assertTrue(any("COMIDA" in a for a in final["budget_alerts"]))
        self.assertAlmostEqual(final["fx_rate"] or 0.0, 1.10)
        self.assertIn("# Informe de gastos", final["final_report"])
        self.assertIn("502.00", final["final_report"])
        self.assertEqual(final["current_step"], "done")


class TestReporter(unittest.TestCase):
    def test_sin_tasa_avisa_y_no_convierte(self) -> None:
        state = initial_finance_state("", "", False)
        state.update(
            {
                "filename": "x.csv",
                "row_count": 1,
                "date_from": "2026-01-01",
                "date_to": "2026-01-01",
                "skipped_rows": 0,
                "totals": {"OCIO": {"EUR": 0.0, "USD": 100.0}},
                "messages": [AIMessage(content="- Hallazgo.")],
            }
        )
        patch = reporter_node(state)
        self.assertIsNone(patch["fx_rate"])
        self.assertIn("sin convertir", patch["final_report"])
        self.assertEqual(patch["findings"], ["Hallazgo."])


class TestRealMCPServer(unittest.TestCase):
    def test_stdio_roundtrip_budget(self) -> None:
        """Servidor MCP real por stdio: get_budget_limit responde."""
        import json

        from src.finance.mcp_tools import mcp_session_tools

        async def go() -> str:
            async with mcp_session_tools() as tools:
                names = sorted(t.name for t in tools)
                self.assertEqual(names, ["get_budget_limit", "get_eur_usd_rate"])
                budget = next(t for t in tools if t.name == "get_budget_limit")
                return await budget.ainvoke({"categoria": "COMIDA"})

        out = asyncio.run(go())
        self.assertEqual(json.loads(out)["limit_eur"], 300.0)


class TestFinanceApi(unittest.TestCase):
    def test_post_con_csv_y_sin_csv(self) -> None:
        import os

        os.environ["API_MODE"] = "demo"
        from fastapi.testclient import TestClient

        from api.main import app
        from config.settings import get_settings

        get_settings.cache_clear()
        client = TestClient(app)

        res = client.post(
            "/api/finance/run",
            files={"file": ("gastos.csv", MOCK_CSV.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        body = res.json()
        self.assertEqual(body["mode"], "demo")
        self.assertFalse(body["used_mock"])
        self.assertEqual(body["row_count"], 12)
        self.assertIn("tools", body["path"])
        self.assertIn("# Informe de gastos", body["final_report"])
        # Las tools MCP respondieron de verdad (no errores silenciosos).
        self.assertTrue(any("COMIDA" in a for a in body["budget_alerts"]), body["budget_alerts"])
        self.assertIsNotNone(body["fx_rate"])
        self.assertEqual(body["tool_iterations"], 1)

        res2 = client.post("/api/finance/run")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()["used_mock"])

    def test_csv_invalido_422(self) -> None:
        import os

        os.environ["API_MODE"] = "demo"
        from fastapi.testclient import TestClient

        from api.main import app
        from config.settings import get_settings

        get_settings.cache_clear()
        client = TestClient(app)
        res = client.post(
            "/api/finance/run", files={"file": ("x.csv", b"a,b\n1,2", "text/csv")}
        )
        self.assertEqual(res.status_code, 422)

    def test_jobs_y_stream_mock(self) -> None:
        import json
        import os

        os.environ["API_MODE"] = "demo"
        from fastapi.testclient import TestClient

        from api.main import app
        from config.settings import get_settings

        get_settings.cache_clear()
        client = TestClient(app)

        job = client.post("/api/finance/jobs")
        self.assertEqual(job.status_code, 200)
        job_id = job.json()["job_id"]
        self.assertTrue(job_id)

        with client.stream("GET", "/api/finance/stream", params={"job_id": job_id}) as res:
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/event-stream", res.headers["content-type"])
            text = res.read().decode()
        self.assertIn("event: start", text)
        self.assertIn("event: node", text)
        self.assertIn("event: route", text)
        self.assertIn('"to": "reporter"', text)
        self.assertIn('"kind": "finance"', text)
        self.assertIn("event: done", text)
        done_line = next(ln for ln in text.splitlines() if ln.startswith("data: ") and "Informe de gastos" in ln)
        done = json.loads(done_line[len("data: "):])
        self.assertTrue(done["used_mock"])
        self.assertTrue(any("COMIDA" in a for a in done["budget_alerts"]))

    def test_stream_job_desconocido_404(self) -> None:
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        res = client.get("/api/finance/stream", params={"job_id": "noexiste"})
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
