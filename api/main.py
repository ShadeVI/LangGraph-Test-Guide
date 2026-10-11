"""App FastAPI del pipeline multi-agente.

Arranque (`uvicorn` viene en requirements.txt; se invoca con `python -m`
para no depender del PATH de Scripts en Windows; el modo se elige en `.env`
con API_MODE=demo|live):
    python -m uvicorn api.main:app --port 8000

Endpoints:
    GET  /api/health      → estado + modo activo.
    GET  /api/config      → configuración pública para la UI.
    POST /api/run         → ejecuta el grafo y devuelve el resultado completo.
    GET  /api/run/stream  → Server-Sent Events: start → node* → done.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config.logging_config import configure_logging, get_logger
from config.settings import get_settings
from src.llm.base import LLMAllProvidersFailedError
from src.llm.factory import PROVIDER_ORDER
from api import service
from api.schemas import ConfigResponse, HealthResponse, RunRequest, RunResponse

logger = get_logger(__name__)


def _cors_origins() -> list[str]:
    """Lee los orígenes permitidos de settings (coma → lista limpia)."""
    raw = get_settings().api_cors_origins
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("API lista (mode=%s, cors=%s).", settings.api_mode, _cors_origins())
    yield


app = FastAPI(title="Multi-Agente API", version="1.0.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Raíz informativa (los endpoints viven bajo /api/*; docs en /docs)."""
    return {"service": "Multi-Agente API", "health": "/api/health", "docs": "/docs"}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Sonda de vida: confirma que la API responde y en qué modo."""
    return HealthResponse(mode=get_settings().api_mode)


@app.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    """Configuración pública (sin secretos) para adaptar la UI."""
    settings = get_settings()
    return ConfigResponse(
        mode=settings.api_mode,
        max_revisions_default=settings.max_revisions,
        providers_order=list(PROVIDER_ORDER),
        cors_origins=_cors_origins(),
    )


@app.post("/api/run", response_model=RunResponse)
def run(req: RunRequest) -> RunResponse:
    """Ejecuta el pipeline completo (bloqueante; en live tarda ~30-60s)."""
    settings = get_settings()
    try:
        return service.run_pipeline(req.query, req.max_revisions, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMAllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=f"Todos los proveedores fallaron: {exc}") from exc


@app.get("/api/run/stream")
def run_stream(
    query: str = Query(min_length=3, max_length=500),
    max_revisions: int = Query(default=2, ge=0, le=5),
) -> StreamingResponse:
    """Retransmite la ejecución nodo a nodo por SSE (ideal para la demo web)."""
    settings = get_settings()
    return StreamingResponse(
        service.stream_pipeline(query, max_revisions, settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
