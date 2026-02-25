"""
Health check endpoint.

Sirve para verificar que la API está viva.
Docker y los balanceadores de carga lo usan
para saber si el contenedor está sano.
"""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """Devuelve el estado de la API."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }