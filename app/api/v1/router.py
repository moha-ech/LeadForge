"""Router principal de la API v1. Agrupa todos los sub-routers."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_v1_router = APIRouter()

# Registrar sub-routers
api_v1_router.include_router(health_router, tags=["Health"])

# Aquí iremos añadiendo más:
# api_v1_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
