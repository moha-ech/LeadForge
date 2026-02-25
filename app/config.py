"""
Configuración central de LeadForge.

Usa Pydantic BaseSettings para leer variables de entorno
y validarlas automáticamente al arrancar la aplicación.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    POSTGRES_USER: str = "leadforge"
    POSTGRES_PASSWORD: str = "leadforge_secret"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "leadforge"

    @property
    def database_url(self) -> str:
        """Genera la URL de conexión a PostgreSQL para SQLAlchemy async."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        """Genera la URL de conexión a Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Celery ---
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

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