"""
Entry point de la aplicación FastAPI.

Crea la app, registra routers y configura middlewares.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.config import get_settings
from app.api.v1.router import api_v1_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestiona el ciclo de vida de la aplicación.
    
    - startup: lo que ocurre al arrancar (conectar DB, etc.)
    - shutdown: lo que ocurre al parar (cerrar conexiones, etc.)
    """
    # --- Startup ---
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} arrancando...")
    yield
    # --- Shutdown ---
    print(f"👋 {settings.APP_NAME} cerrándose...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de captación, enriquecimiento y cualificación automática de leads",
    lifespan=lifespan,
)

# Registrar routers
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)