"""Endpoints del flujo financiero: subida de CSV (o mock) → informe Markdown.

  POST /api/finance/run   multipart con campo `file` (.csv, ≤1 MB).
                          Sin fichero se analiza el mock incorporado.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from config.logging_config import get_logger
from config.settings import get_settings
from src.finance.service import run_finance_analysis
from src.finance.state import MAX_CSV_BYTES, FinanceInputError
from src.llm.base import LLMAllProvidersFailedError
from api.finance_schemas import FinanceResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.post("/run", response_model=FinanceResponse)
async def run_finance(file: UploadFile | None = File(None)) -> FinanceResponse:
    """Analiza un CSV de gastos (o el mock) con agentes + tools MCP.

    Args:
        file: Fichero .csv (fecha,concepto,categoria,importe,moneda).

    Returns:
        Totales, alertas, tasa, hallazgos, informe Markdown y trazabilidad.
    """
    settings = get_settings()
    if file is None or not file.filename:
        logger.info("API finance: sin fichero, se usará el mock.")
        return await run_finance_analysis("", "mock_gastos.csv", True, settings)
    raw = await file.read()
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="Fichero mayor de 1 MB.")
    try:
        csv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="El CSV debe estar en UTF-8.") from exc
    try:
        return await run_finance_analysis(csv_text, file.filename, False, settings)
    except FinanceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMAllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=f"Todos los proveedores fallaron: {exc}") from exc
