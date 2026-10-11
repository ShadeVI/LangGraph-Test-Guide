"""Contrato Strategy + excepciones del subsistema LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProviderError(RuntimeError):
    """Fallo recuperable de un proveedor concreto (red, cuota, credenciales)."""


class LLMConfigurationError(LLMProviderError):
    """Mala configuración (p. ej. falta la API key): no es transitorio.

    Se registra una sola vez al arrancar (INFO), no como WARNING en cada
    llamada, para no inundar los logs cuando un proveedor está ausente.
    """


class LLMAllProvidersFailedError(RuntimeError):
    """Todos los proveedores del fallback fallaron; el grafo no puede continuar."""


class LLMStrategy(ABC):
    """Interfaz Strategy: cada proveedor implementa la misma operación.

    Cumple OCP: añadir un proveedor nuevo = añadir una subclase,
    sin modificar el cliente resiliente ni los agentes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre humano del proveedor (p. ej. ``"groq"``)."""
        ...

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Genera una completación de texto para el prompt dado.

        Args:
            prompt: Instrucción completa (system + contexto) para el LLM.

        Returns:
            Texto generado por el proveedor.

        Raises:
            LLMProviderError: Ante cualquier fallo recuperable.
        """
        ...
