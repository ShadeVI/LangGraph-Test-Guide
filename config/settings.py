"""Ajustes tipados cargados desde entorno (.env).

Centraliza toda la configuración para cumplir DIP: el resto del
código depende de esta abstracción, no de ``os.environ`` disperso.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración inmutable de la aplicación.

    Attributes:
        groq_api_key: API key de Groq (opcional; si falta, el proveedor falla con gracia).
        gemini_api_key: API key de Gemini de AI Studio (opcional; vale GEMINI_API_KEY
            o la clásica GOOGLE_API_KEY como fallback).
        groq_model: Modelo de Groq por defecto.
        gemini_model: Modelo de Gemini por defecto.
        ollama_model: Modelo local de Ollama por defecto.
        ollama_base_url: URL base del servidor Ollama local.
        ollama_num_predict: Tope de tokens generados por llamada (clave en CPU).
        ollama_think: Razonamiento interno del modelo (en CPU, desactivar).
        llm_temperature: Temperatura común a todos los proveedores.
        llm_timeout: Timeout en segundos por invocación LLM.
        log_level: Nivel de logging raíz (INFO, DEBUG, WARNING, ERROR).
        max_revisions: Nº máximo de vueltas editor→writer antes de forzar END.
        api_mode: "demo" (LLM guionizado, sin keys) o "live" (Groq→Gemini→Ollama).
        api_cors_origins: Orígenes permitidos por la API, separados por comas.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_api_key: str = Field(
        default="", validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY")
    )

    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    gemini_model: str = Field(default="gemini-flash-latest", alias="GEMINI_MODEL")
    ollama_model: str = Field(default="qwen3.5:4b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_num_predict: int = Field(default=1024, alias="OLLAMA_NUM_PREDICT")
    ollama_think: bool = Field(default=False, alias="OLLAMA_THINK")

    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_timeout: int = Field(default=60, alias="LLM_TIMEOUT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_revisions: int = Field(default=2, alias="MAX_REVISIONS")
    api_mode: str = Field(default="demo", alias="API_MODE")
    api_cors_origins: str = Field(
        default="http://localhost:4200,http://127.0.0.1:4200", alias="API_CORS_ORIGINS"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia singleton de :class:`Settings`.

    Returns:
        Settings: Configuración cacheada de la aplicación.
    """
    return Settings()
