"""Clase base de agentes (Template Method + DIP)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import time

from config.logging_config import get_logger
from src.llm.resilient_client import ResilientLLMClient
from src.state import GraphState

#: Patch parcial que un agente devuelve; `run` lo normaliza a GraphState.
AgentPatch = dict[str, Any]


class BaseAgent(ABC):
    """Plantilla común: logging de ciclo de vida + delegación a `_execute`.

    Args:
        llm: Cliente resiliente con fallback (inyectado, no creado aquí).
        node_name: Nombre del nodo en el grafo (para logs y `current_step`).
    """

    def __init__(self, llm: ResilientLLMClient, node_name: str) -> None:
        self._llm = llm
        self._node_name = node_name
        self._logger = get_logger(f"{__name__}.{node_name}")

    @property
    def node_name(self) -> str:
        """Returns: Nombre del nodo que este agente ejecuta."""
        return self._node_name

    def run(self, state: GraphState) -> dict[str, Any]:
        """Ejecuta el agente con logging de entrada/salida.

        Mide duración, acumula trazabilidad (`providers_used`, `errors`) y
        registra la ruta recorrida (`path`) para evidenciar flujos no lineales.

        Args:
            state: Estado entrante del grafo.

        Returns:
            Patch parcial del estado (claves actualizadas).
        """
        self._logger.info("▶ Iniciando nodo '%s'.", self._node_name)
        started = time.perf_counter()
        patch: AgentPatch = self._execute(state)
        elapsed = time.perf_counter() - started
        patch["current_step"] = self._node_name
        # Trazabilidad acumulativa sin mutar las listas originales del estado.
        patch["providers_used"] = list(state.get("providers_used", [])) + list(patch.pop("_providers_used", []))
        patch["errors"] = list(state.get("errors", [])) + list(patch.pop("_errors", []))
        patch["path"] = [*state.get("path", []), self._node_name]
        self._logger.info("✔ Nodo '%s' finalizado en %.2fs.", self._node_name, elapsed)
        return patch

    @abstractmethod
    def _execute(self, state: GraphState) -> AgentPatch:
        """Lógica específica del agente. Devuelve patch parcial del estado."""
        ...
