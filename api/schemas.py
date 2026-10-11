"""Esquemas Pydantic de la API (contratos de entrada/salida validados)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Petición de ejecución del pipeline.

    Attributes:
        query: Consulta a procesar (3–500 caracteres).
        max_revisions: Vueltas máximas del ciclo editor→writer (0–5).
    """

    query: str = Field(min_length=3, max_length=500)
    max_revisions: int = Field(default=2, ge=0, le=5)


class RunResponse(BaseModel):
    """Resultado completo de una ejecución del grafo.

    Attributes:
        query: Consulta procesada.
        mode: "demo" (LLM guionizado) o "live" (proveedores reales).
        final_report: Informe Markdown final.
        path: Nodos recorridos en orden.
        providers_used: Proveedor ganador de cada llamada LLM.
        errors: Fallos recuperados vía fallback.
        revision_count: Revisiones realizadas.
        current_step: Paso final ("done").
        editor_feedback: Último motivo de REVISAR (vacío si se aprobó).
        research_points: Puntos extraídos (para inspeccionar el estado final).
        draft: Último borrador (para inspeccionar el estado final).
    """

    query: str
    mode: str
    final_report: str
    path: list[str] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    revision_count: int = 0
    current_step: str = "done"
    editor_feedback: str = ""
    research_points: list[str] = Field(default_factory=list)
    draft: str = ""


class HealthResponse(BaseModel):
    """Estado del servicio."""

    status: str = "ok"
    mode: str


class ConfigResponse(BaseModel):
    """Configuración pública (sin secretos) para que la UI se adapte."""

    mode: str
    max_revisions_default: int
    providers_order: list[str]
    cors_origins: list[str] = Field(default_factory=list)
    graph: str = "researcher -> writer -> editor -[REVISAR]-> writer / -[APROBADO]-> END"
