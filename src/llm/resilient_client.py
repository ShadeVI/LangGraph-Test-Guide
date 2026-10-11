"""Cliente resiliente con fallback ordenado (Groq → Gemini → Ollama)."""

from __future__ import annotations

from dataclasses import dataclass

from config.logging_config import get_logger
from src.llm.base import (
    LLMAllProvidersFailedError,
    LLMConfigurationError,
    LLMProviderError,
    LLMStrategy,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class GenerationResult:
    """Resultado trazable de una generación.

    Attributes:
        text: Texto generado por el proveedor ganador.
        provider: Nombre del proveedor que respondió.
        attempted: Proveedores intentados en orden.
        failures: Mensajes de fallo por proveedor (vacío si ganó el primero).
    """

    text: str
    provider: str
    attempted: tuple[str, ...]
    failures: tuple[str, ...]


class ResilientLLMClient:
    """Orquesta estrategias LLM con tolerancia a fallos.

    Recorre las estrategias en orden de prioridad; ante
    :class:`LLMProviderError` registra un WARNING y continúa con la
    siguiente. El flujo global del grafo nunca se interrumpe por el
    fallo de un único proveedor.

    Args:
        strategies: Estrategias en orden de prioridad. Debe haber ≥ 1.
    """

    def __init__(self, strategies: list[LLMStrategy]) -> None:
        if not strategies:
            raise ValueError("Se requiere al menos una estrategia LLM.")
        self._strategies = list(strategies)

    @property
    def provider_names(self) -> tuple[str, ...]:
        """Returns: Nombres de proveedores en orden de prioridad."""
        return tuple(s.name for s in self._strategies)

    def generate(self, prompt: str) -> GenerationResult:
        """Genera texto intentando cada proveedor en orden.

        Args:
            prompt: Prompt completo para el LLM.

        Returns:
            Resultado con texto, proveedor ganador y traza de intentos.

        Raises:
            LLMAllProvidersFailedError: Si todos los proveedores fallan.
        """
        failures: list[str] = []
        for strategy in self._strategies:
            logger.info("Probando proveedor LLM: %s", strategy.name)
            try:
                text = strategy.generate(prompt)
                logger.info("Proveedor '%s' respondió correctamente.", strategy.name)
                return GenerationResult(
                    text=text,
                    provider=strategy.name,
                    attempted=self.provider_names,
                    failures=tuple(failures),
                )
            except LLMConfigurationError as exc:
                # Config ausente: se sabe desde el arranque (ver factory); no es
                # un incidente, así que se registra en INFO y se sigue.
                failures.append(f"[{strategy.name}] {exc}")
                logger.info("Proveedor '%s' omitido: %s", strategy.name, exc)
            except LLMProviderError as exc:
                msg = f"[{strategy.name}] {exc}"
                failures.append(msg)
                logger.warning("Fallo proveedor '%s': %s. Aplicando fallback…", strategy.name, exc)
            except Exception as exc:  # noqa: BLE001 — robustez ante errores imprevistos
                msg = f"[{strategy.name}] error inesperado: {exc}"
                failures.append(msg)
                logger.error("Error inesperado en '%s': %s. Aplicando fallback…", strategy.name, exc)
        logger.error("Todos los proveedores LLM fallaron (%d intentos).", len(self._strategies))
        raise LLMAllProvidersFailedError(" | ".join(failures))
