"""Tests de la API REST (TestClient, modo demo: sin red externa ni keys).

Ejecutar:  python tests/test_api.py
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["API_MODE"] = "demo"

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from config.settings import get_settings  # noqa: E402

get_settings.cache_clear()
client = TestClient(app)


class TestApi(unittest.TestCase):
    def test_health_responde_modo_demo(self) -> None:
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok", "mode": "demo"})

    def test_config_expone_orden_sin_secretos(self) -> None:
        res = client.get("/api/config")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["providers_order"], ["groq", "gemini", "ollama"])
        self.assertIn("http://localhost:4200", body["cors_origins"])
        self.assertNotIn("groq_api_key", res.text.lower())

    def test_run_demo_recorre_el_ciclo(self) -> None:
        res = client.post("/api/run", json={"query": "¿Qué es LangGraph?", "max_revisions": 2})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["mode"], "demo")
        self.assertEqual(
            body["path"], ["researcher", "writer", "editor", "writer", "editor"]
        )
        self.assertEqual(body["revision_count"], 1)
        self.assertTrue(body["final_report"].startswith("# Informe demo"))
        self.assertEqual(body["current_step"], "done")
        self.assertEqual(len(body["research_points"]), 3)
        self.assertIn("corregido", body["draft"])

    def test_run_rechaza_query_corta(self) -> None:
        res = client.post("/api/run", json={"query": "ab"})
        self.assertEqual(res.status_code, 422)

    def test_stream_emite_nodos_y_done(self) -> None:
        with client.stream("GET", "/api/run/stream", params={"query": "Demo SSE"}) as res:
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/event-stream", res.headers["content-type"])
            text = res.read().decode()
        self.assertIn("event: start", text)
        self.assertIn('"entry": "researcher"', text)
        self.assertIn("event: node", text)
        self.assertIn("event: done", text)
        self.assertIn('"revision_count": 1', text)
        self.assertIn("Borrador Nº 2 redactado", text)
        self.assertIn("Veredicto: REVISAR", text)
        self.assertIn("Veredicto: APROBADO", text)
        self.assertIn("event: route", text)
        self.assertIn('"to": "writer"', text)
        self.assertIn('"to": "end"', text)
        self.assertIn('"snapshot"', text)
        self.assertIn('"research_points"', text)

    def test_stream_rechaza_query_corta(self) -> None:
        res = client.get("/api/run/stream", params={"query": "ab"})
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
