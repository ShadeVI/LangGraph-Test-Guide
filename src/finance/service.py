"""Casos de uso del flujo financiero: ejecución async con sesión MCP propia.

Cada ejecución abre UNA sesión contra ``python -m mcp_server.server``,
inyecta sus tools al grafo y la cierra al terminar (sin estado compartido).
"""

from __future__ import annotations

from config.logging_config import get_logger
from config.settings import Settings
from src.finance.builder import MAX_TOOL_ITERATIONS, build_finance_graph
from src.finance.demo_llm import ScriptedFinanceLLM
from src.finance.mcp_tools import mcp_session_tools
from src.finance.state import FinanceInputError, FinanceState, initial_finance_state
from src.llm.base import LLMAllProvidersFailedError
from src.llm.factory import build_resilient_client
from src.llm.resilient_client import ResilientLLMClient
from api.finance_schemas import FinanceResponse

logger = get_logger(__name__)

DEMO_MODE = "demo"
LIVE_MODE = "live"

#: Errores de dominio que deben emerger tal cual aunque anyio/MCP los
#: envuelvan en ExceptionGroup durante el teardown de la sesión.
_DOMAIN_ERRORS = (FinanceInputError, LLMAllProvidersFailedError)


def resolve_finance_client(settings: Settings) -> tuple[ResilientLLMClient, str]:
    """Devuelve (cliente LLM, modo) para el analista financiero.

    En demo el analista es guionizado (pero las tools MCP son las reales);
    en live usa la cadena Groq → Gemini → Ollama con function calling.
    """
    mode = (settings.api_mode or DEMO_MODE).strip().lower()
    if mode == LIVE_MODE:
        return build_resilient_client(settings), LIVE_MODE
    if mode != DEMO_MODE:
        logger.warning("API_MODE=%r desconocido; se usa 'demo'.", settings.api_mode)
    return ResilientLLMClient([ScriptedFinanceLLM()]), DEMO_MODE


def _unwrap_domain_error(exc: BaseException) -> BaseException | None:
    """Busca un error de dominio dentro de ExceptionGroups anidados.

    Args:
        exc: Excepción capturada (posible ExceptionGroup de anyio/MCP).

    Returns:
        El FinanceInputError / LLMAllProvidersFailedError encontrado, o None.
    """
    if isinstance(exc, _DOMAIN_ERRORS):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            found = _unwrap_domain_error(sub)
            if found is not None:
                return found
    return None


def to_finance_response(
    filename: str, used_mock: bool, mode: str, final: FinanceState
) -> FinanceResponse:
    """Convierte el estado final en respuesta HTTP validada."""
    return FinanceResponse(
        filename=filename,
        used_mock=used_mock,
        mode=mode,
        row_count=final.get("row_count", 0),
        totals=final.get("totals", {}),
        fx_rate=final.get("fx_rate"),
        fx_date=final.get("fx_date", ""),
        fx_source=final.get("fx_source", ""),
        fx_stale=final.get("fx_stale", False),
        budget_alerts=list(final.get("budget_alerts", [])),
        findings=list(final.get("findings", [])),
        final_report=final.get("final_report", ""),
        path=list(final.get("path", [])),
        providers_used=list(final.get("providers_used", [])),
        errors=list(final.get("errors", [])),
        tool_iterations=final.get("tool_iterations", 0),
        current_step=final.get("current_step", "done"),
    )


async def run_finance_analysis(
    csv_text: str,
    filename: str,
    used_mock: bool,
    settings: Settings,
    max_tool_iters: int = MAX_TOOL_ITERATIONS,
) -> FinanceResponse:
    """Ejecuta el grafo financiero completo (para POST /api/finance/run).

    Raises:
        FinanceInputError: Si el CSV es inválido.
        LLMAllProvidersFailedError: Si todos los proveedores fallan (live).
    """
    llm, mode = resolve_finance_client(settings)
    logger.info("API finance: ejecución %s de %r.", mode, filename)
    try:
        async with mcp_session_tools() as tools:
            graph = build_finance_graph(llm, tools, max_tool_iters)
            final: FinanceState = await graph.ainvoke(
                initial_finance_state(csv_text, filename, used_mock)
            )
    except BaseException as exc:
        # anyio/MCP envuelven los fallos en ExceptionGroup al cerrar la sesión;
        # los errores de dominio deben emerger tal cual (422/502 en la API).
        domain = _unwrap_domain_error(exc)
        raise domain if domain is not None else exc
    logger.info("API finance: fin %s, ruta=%s.", mode, " -> ".join(final.get("path", [])))
    return to_finance_response(filename, used_mock, mode, final)
