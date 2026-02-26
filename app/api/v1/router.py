"""Router principal de la API v1. Agrupa todos los sub-routers."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.leads import router as leads_router

api_v1_router = APIRouter()

# Registrar sub-routers
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(leads_router, prefix="/leads", tags=["Leads"])