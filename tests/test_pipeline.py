"""Tests de resiliencia y del pipeline (dobles de prueba, sin red ni API keys).

Ejecutar:  python tests/test_pipeline.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langchain_core.messages import AIMessage  # noqa: E402

from config.logging_config import configure_logging  # noqa: E402
from src.agents.editor import EditorAgent  # noqa: E402
from src.graph.builder import (  # noqa: E402
    ROUTE_TO_END,
    ROUTE_TO_WRITER,
    build_graph_with_llm,
    make_router,
)
from src.llm.base import LLMProviderError, LLMStrategy  # noqa: E402
from src.llm.base import LLMConfigurationError  # noqa: E402
from src.llm.groq_strategy import GroqStrategy  # noqa: E402
from src.llm.factory import build_resilient_client  # noqa: E402
from src.llm.resilient_client import (  # noqa: E402
    LLMAllProvidersFailedError,
    ResilientLLMClient,
)
from src.state import initial_state  # noqa: E402

configure_logging("ERROR")


class FakeFailingStrategy(LLMStrategy):
    """Doble que siempre falla (simula rate limit / red caída)."""

    def __init__(self, name: str = "failing") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def generate(self, prompt: str) -> str:
        raise LLMProviderError(f"{self._name}: 429 rate limit simulado")


class FakeSuccessStrategy(LLMStrategy):
    """Doble que responde de forma determinista y cuenta llamadas."""

    def __init__(self, name: str = "fake", payload: str = "- punto A\n- punto B") -> None:
        self._name = name
        self._payload = payload
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    def generate(self, prompt: str) -> str:
        self.calls += 1
        assert prompt, "El prompt no debe estar vacío"
        return self._payload


class ScriptedLLM(LLMStrategy):
    """Doble con guion por rol: detecta el agente por su prompt y sirve réplicas en orden."""

    def __init__(
        self,
        research: str = "- Alpha\n- Beta",
        writers: list[str] | None = None,
        editors: list[str] | None = None,
    ) -> None:
        self._research = research
        self._writers = writers or ["Borrador sobre Alpha y Beta."]
        self._editors = editors or ["VEREDICTO: APROBADO\n\n# Informe\n\nTexto final."]
        self._w = 0
        self._e = 0

    @property
    def name(self) -> str:
        return "scripted"

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


class TestResilientClient(unittest.TestCase):
    def test_fallback_usa_segundo_proveedor_tras_fallo(self) -> None:
        failing = FakeFailingStrategy("groq-mock")
        success = FakeSuccessStrategy("gemini-mock", payload="OK")
        client = ResilientLLMClient([failing, success])
        result = client.generate("hola")
        self.assertEqual(result.text, "OK")
        self.assertEqual(result.provider, "gemini-mock")
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(success.calls, 1)

    def test_todos_fallan_lanza_error_agregado(self) -> None:
        client = ResilientLLMClient([FakeFailingStrategy("a"), FakeFailingStrategy("b")])
        with self.assertRaises(LLMAllProvidersFailedError):
            client.generate("hola")

    def test_sin_estrategias_lanza_value_error(self) -> None:
        with self.assertRaises(ValueError):
            ResilientLLMClient([])

    def test_factory_respeta_orden_groq_gemini_ollama(self) -> None:
        from config.settings import Settings

        client = build_resilient_client(Settings(_env_file=None))
        self.assertEqual(client.provider_names, ("groq", "gemini", "ollama"))

    def test_falta_de_key_es_error_de_configuracion(self) -> None:
        """Sin API key el error es LLMConfigurationError (subtipo recuperable)."""
        from config.settings import Settings

        strategy = GroqStrategy(Settings(_env_file=None))
        with self.assertRaises(LLMConfigurationError):
            strategy.generate("hola")
        with self.assertRaises(LLMProviderError):  # sigue capturándolo el fallback
            strategy.generate("hola")

    def test_error_configuracion_hace_fallback_igual(self) -> None:
        from config.settings import Settings

        client = ResilientLLMClient(
            [GroqStrategy(Settings(_env_file=None)), FakeSuccessStrategy("ok", "OK")]
        )
        result = client.generate("hola")
        self.assertEqual(result.provider, "ok")
        self.assertEqual(len(result.failures), 1)


class TestGeminiConverters(unittest.TestCase):
    """Conversores genai↔LangChain sin red (la API real se prueba en vivo)."""

    def test_to_contents_mapea_roles(self) -> None:
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        from src.llm.gemini_strategy import _to_contents

        system, contents = _to_contents(
            [
                SystemMessage(content="Eres analista."),
                HumanMessage(content="Analiza esto."),
                ToolMessage(content='{"limit_eur": 300}', name="get_budget_limit", tool_call_id="c1"),
            ]
        )
        self.assertEqual(system, "Eres analista.")
        self.assertEqual([c.role for c in contents], ["user", "user"])
        self.assertEqual(contents[1].parts[0].function_response.name, "get_budget_limit")

    def test_to_contents_ai_con_tools(self) -> None:
        from src.llm.gemini_strategy import _to_contents

        _, contents = _to_contents(
            [AIMessage(content="", tool_calls=[{"name": "fx", "args": {}, "id": "1", "type": "tool_call"}])]
        )
        part = contents[0].parts[0]
        self.assertEqual(part.function_call.name, "fx")

    def test_to_ai_message(self) -> None:
        from types import SimpleNamespace

        from src.llm.gemini_strategy import _to_ai_message

        response = SimpleNamespace(
            text="listo",
            function_calls=[SimpleNamespace(name="fx", args={"x": 1})],
        )
        message = _to_ai_message(response)
        self.assertEqual(message.content, "listo")
        self.assertEqual(message.tool_calls[0]["name"], "fx")
        self.assertEqual(message.tool_calls[0]["args"], {"x": 1})
        self.assertTrue(message.tool_calls[0]["id"])
        self.assertIsNone(_to_ai_message(SimpleNamespace(text=None, function_calls=None)).content or None)

    def test_gen_config_sin_thinking(self) -> None:
        from src.llm.gemini_strategy import _gen_config

        from config.settings import Settings

        cfg = _gen_config(Settings(_env_file=None))
        self.assertEqual(cfg.thinking_config.thinking_budget, 0)
        self.assertIsNone(cfg.tools)

    def test_root_message_extrae_error_api(self) -> None:
        from src.llm.gemini_strategy import _root_message

        inner = RuntimeError("429 RESOURCE_EXHAUSTED: cuota superada")
        outer = RuntimeError(f"envuelto: {inner}")
        outer.__cause__ = inner
        self.assertIn("RESOURCE_EXHAUSTED", _root_message(outer))
        self.assertEqual("simple", _root_message(ValueError("simple")))

    def test_cliente_se_reutiliza(self) -> None:
        from src.llm.gemini_strategy import GeminiStrategy

        from config.settings import Settings

        settings = Settings(_env_file=None)
        settings.gemini_api_key = "dummy-solo-construccion"
        strategy = GeminiStrategy(settings)
        self.assertIs(strategy._get_client(), strategy._get_client())


class TestVerdictParsing(unittest.TestCase):
    def test_aprobado(self) -> None:
        needs, feedback, body = EditorAgent._parse_verdict("VEREDICTO: APROBADO\n\n# Doc")
        self.assertFalse(needs)
        self.assertEqual(feedback, "")
        self.assertEqual(body, "# Doc")

    def test_revisar_con_motivo(self) -> None:
        needs, feedback, body = EditorAgent._parse_verdict(
            "VEREDICTO: REVISAR - faltan causas\n\n# Doc parcial"
        )
        self.assertTrue(needs)
        self.assertIn("faltan causas", feedback)
        self.assertEqual(body, "# Doc parcial")

    def test_sin_veredicto_aprueba_por_defecto(self) -> None:
        needs, _, body = EditorAgent._parse_verdict("# Doc sin veredicto")
        self.assertFalse(needs)
        self.assertIn("# Doc", body)


class TestRouter(unittest.TestCase):
    def test_aprobado_lleva_a_end(self) -> None:
        route = make_router(2)({"needs_revision": False, "revision_count": 0})
        self.assertEqual(route, ROUTE_TO_END)

    def test_revisar_bajo_tope_vuelve_a_writer(self) -> None:
        route = make_router(2)({"needs_revision": True, "revision_count": 1})
        self.assertEqual(route, ROUTE_TO_WRITER)

    def test_revisar_en_tope_fuerza_end(self) -> None:
        route = make_router(2)({"needs_revision": True, "revision_count": 2})
        self.assertEqual(route, ROUTE_TO_END)

    def test_max_negativo_rechazado(self) -> None:
        with self.assertRaises(ValueError):
            make_router(-1)


class TestPipeline(unittest.TestCase):
    def test_end_to_end_nominal_sin_revisiones(self) -> None:
        """Ruta lineal researcher→writer→editor→END con veredicto APROBADO."""
        graph = build_graph_with_llm(ResilientLLMClient([ScriptedLLM()]), max_revisions=2)
        final = graph.invoke(initial_state("Tema de prueba"))
        self.assertEqual(final["research_points"], ["Alpha", "Beta"])
        self.assertIn("Borrador", final["draft"])
        self.assertTrue(final["final_report"].startswith("# Informe"))
        self.assertEqual(final["current_step"], "done")
        self.assertEqual(final["revision_count"], 0)
        self.assertEqual(final["path"], ["researcher", "writer", "editor"])

    def test_loop_revision_vuelve_a_writer_y_aprueba(self) -> None:
        """Ruta no lineal: editor REVISAR → writer v2 → editor APROBADO → END."""
        llm = ScriptedLLM(
            writers=["Borrador flojo.", "Borrador corregido y completo."],
            editors=[
                "VEREDICTO: REVISAR - demasiado superficial\n\n# Parcial",
                "VEREDICTO: APROBADO\n\n# Informe v2\n\nTexto final.",
            ],
        )
        graph = build_graph_with_llm(ResilientLLMClient([llm]), max_revisions=2)
        final = graph.invoke(initial_state("Tema con revisión"))
        self.assertEqual(
            final["path"], ["researcher", "writer", "editor", "writer", "editor"]
        )
        self.assertEqual(final["revision_count"], 1)
        self.assertIn("corregido", final["draft"])
        self.assertTrue(final["final_report"].startswith("# Informe v2"))
        self.assertEqual(final["current_step"], "done")

    def test_tope_revisiones_termina_aunque_pida_revisar(self) -> None:
        """Garantía de terminación: con REVISAR eterno y max=1, el grafo acaba."""
        llm = ScriptedLLM(
            editors=["VEREDICTO: REVISAR - nunca conforme\n\n# Parcial"],
        )
        graph = build_graph_with_llm(ResilientLLMClient([llm]), max_revisions=1)
        final = graph.invoke(initial_state("Tema imposible"))
        self.assertEqual(
            final["path"], ["researcher", "writer", "editor", "writer", "editor"]
        )
        self.assertEqual(final["current_step"], "done")
        self.assertTrue(final["final_report"].startswith("# Parcial"))

    def test_initial_state_rechaza_vacio(self) -> None:
        with self.assertRaises(ValueError):
            initial_state("   ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
