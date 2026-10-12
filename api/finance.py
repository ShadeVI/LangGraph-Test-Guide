"""Endpoints del flujo financiero: subida de CSV (o mock) → informe Markdown.

  POST /api/finance/jobs    guarda el CSV validado y devuelve {job_id}.
  GET  /api/finance/stream  ejecuta el job por SSE: start → (node → route)* → done.
  POST /api/finance/run     atajo directo (multipart) sin streaming.

Sin fichero se analiza el mock incorporado. Límite: 1 MB, UTF-8.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from config.logging_config import get_logger
from config.settings import get_settings
from src.finance.service import run_finance_analysis, stream_finance_analysis
from src.finance.state import MAX_CSV_BYTES, FinanceInputError
from src.llm.base import LLMAllProvidersFailedError
from api.finance_schemas import FinanceResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/finance", tags=["finance"])

#: Trabajos pendientes: job_id → (csv_text, filename, used_mock). Acotado.
_JOBS: OrderedDict[str, tuple[str, str, bool]] = OrderedDict()
MAX_JOBS = 20


async def _read_upload(file: UploadFile | None) -> tuple[str, str, bool]:
    """Valida el multipart y devuelve (csv_text, filename, used_mock).

    Raises:
        HTTPException: 413 si excede 1 MB, 422 si no es UTF-8.
    """
    if file is None or not file.filename:
        logger.info("API finance: sin fichero, se usará el mock.")
        return "", "mock_gastos.csv", True
    raw = await file.read()
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="Fichero mayor de 1 MB.")
    try:
        return raw.decode("utf-8-sig"), file.filename, False
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="El CSV debe estar en UTF-8.") from exc


def _store_job(csv_text: str, filename: str, used_mock: bool) -> str:
    """Guarda el trabajo acotando el almacén. Returns: job_id."""
    while len(_JOBS) >= MAX_JOBS:
        _JOBS.popitem(last=False)
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = (csv_text, filename, used_mock)
    return job_id


@router.post("/jobs")
async def create_job(file: UploadFile | None = File(None)) -> dict[str, str]:
    """Valida y guarda el CSV para ejecutarlo por streaming. Returns: {job_id}."""
    csv_text, filename, used_mock = await _read_upload(file)
    job_id = _store_job(csv_text, filename, used_mock)
    logger.info("API finance: job %s creado (%r, mock=%s).", job_id, filename, used_mock)
    return {"job_id": job_id}


@router.get("/stream")
async def stream_job(job_id: str = Query(min_length=1, max_length=32)) -> StreamingResponse:
    """Retransmite el análisis del job nodo a nodo por SSE."""
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="job_id desconocido o caducado.")
    csv_text, filename, used_mock = _JOBS[job_id]
    settings = get_settings()
    return StreamingResponse(
        stream_finance_analysis(csv_text, filename, used_mock, settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/run", response_model=FinanceResponse)
async def run_finance(file: UploadFile | None = File(None)) -> FinanceResponse:
    """Analiza un CSV de gastos (o el mock) y devuelve el resultado completo."""
    settings = get_settings()
    csv_text, filename, used_mock = await _read_upload(file)
    try:
        return await run_finance_analysis(csv_text, filename, used_mock, settings)
    except FinanceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMAllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=f"Todos los proveedores fallaron: {exc}") from exc
