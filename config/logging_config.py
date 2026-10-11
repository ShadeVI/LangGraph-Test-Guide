"""Configuración profesional de logging (sin ``print`` crudos)."""

from __future__ import annotations

import logging
import sys
import warnings


_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configura el logging raíz con formato estructurado.

    Args:
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR). Inválidos caen a INFO.
    """
    global _CONFIGURED
    numeric = getattr(logging, level.upper(), logging.INFO)
    if _CONFIGURED:
        logging.getLogger().setLevel(numeric)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(numeric)
    root.handlers.clear()
    root.addHandler(handler)
    # Silencia ruido de terceros sin ocultar warnings reales.
    for noisy in ("httpx", "urllib3", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # LangGraph 0.2 en Python 3.15 emite este DeprecationWarning en cada nodo;
    # es de la librería, no de nuestro código: se ignora para no ensuciar.
    warnings.filterwarnings(
        "ignore",
        message=".*asyncio.iscoroutinefunction.*",
        category=DeprecationWarning,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger hijo del raíz ya configurado.

    Args:
        name: Nombre del logger (normalmente ``__name__``).

    Returns:
        Logger configurado.
    """
    return logging.getLogger(name)
