"""
Dependencias de autenticación para los endpoints.

Implementa autenticación por API Key via header.
Las API Keys se definen en la configuración (.env).
En producción usarías una tabla en BD con keys hasheadas.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

settings = get_settings()

# Define que la API Key viene en el header "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    Valida que el request incluye una API Key válida.

    Uso en un endpoint:
        @router.post("/leads")
        async def create_lead(
            data: LeadCreate,
            api_key: str = Depends(require_api_key),
        ):
            ...

    Si no hay key o es inválida, devuelve 401.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Envía el header X-API-Key.",
        )

    if api_key not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida.",
        )

    return api_key