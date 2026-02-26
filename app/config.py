"""
Configuración central de LeadForge.

Usa Pydantic BaseSettings para leer variables de entorno
y validarlas automáticamente al arrancar la aplicación.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- App ---
    APP_NAME: str = "LeadForge"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- API ---
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX")
    API_KEYS: list[str] = os.getenv("API_KEYS")

    # --- Database ---
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: int = os.getenv("POSTGRES_PORT")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")

    @property
    def database_url(self) -> str:
        """Genera la URL de conexión a PostgreSQL para SQLAlchemy async."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = os.getenv("REDIS_PORT")
    REDIS_DB: int = os.getenv("REDIS_DB")

    @property
    def redis_url(self) -> str:
        """Genera la URL de conexión a Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Celery ---
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND")

    def model_post_init(self, __context: object) -> None:
        """Asigna valores por defecto que dependen de otros campos."""
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.redis_url
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.redis_url


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia de configuración (cacheada).
    
    Usar lru_cache asegura que solo se crea una instancia
    de Settings durante toda la vida de la aplicación.
    """
    return Settings()