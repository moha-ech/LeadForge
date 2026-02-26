"""
Endpoints de leads.

Cada endpoint recibe HTTP, delega al servicio, y devuelve HTTP.
No hay lógica de negocio aquí — solo validación, llamada al servicio,
y formateo de respuesta.
"""

from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.dependencies import require_api_key
from app.models.lead import LeadSource, LeadStatus
from app.schemas.lead import (
    LeadCreate,
    LeadEventResponse,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead_service import LeadAlreadyExistsError, LeadService

router = APIRouter()


# --- Dependency: inyecta el servicio con su sesión de BD ---

async def get_lead_service(
    db: AsyncSession = Depends(get_db),
) -> LeadService:
    """Crea una instancia del servicio con la sesión de BD actual."""
    return LeadService(db)


# --- Endpoints ---


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un lead nuevo",
    dependencies=[Depends(require_api_key)],
)
async def create_lead(
    data: LeadCreate,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    """
    Recibe datos de un lead, lo crea y devuelve el lead completo.

    Si el email ya existe, devuelve 409 Conflict.
    Si el dominio del email no es genérico, crea/asocia la empresa.
    """
    try:
        lead = await service.create_lead(data)
    except LeadAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return LeadResponse.model_validate(lead)


@router.get(
    "",
    response_model=LeadListResponse,
    summary="Listar leads con filtros y paginación",
)
async def list_leads(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Leads por página"),
    status: LeadStatus | None = Query(None, description="Filtrar por estado"),
    source: LeadSource | None = Query(None, description="Filtrar por fuente"),
    search: str | None = Query(None, description="Buscar por nombre o email"),
    service: LeadService = Depends(get_lead_service),
) -> LeadListResponse:
    """Devuelve leads paginados con filtros opcionales."""
    leads, total = await service.list_leads(
        page=page,
        size=size,
        status=status,
        source=source.value if source else None,
        search=search,
    )
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 0,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Obtener un lead por ID",
)
async def get_lead(
    lead_id: int,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    """Devuelve el detalle completo de un lead con su empresa."""
    lead = await service.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead con id {lead_id} no encontrado",
        )
    return LeadResponse.model_validate(lead)


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Actualizar un lead",
    dependencies=[Depends(require_api_key)],
)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    """Actualiza solo los campos proporcionados."""
    lead = await service.update_lead(lead_id, data)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead con id {lead_id} no encontrado",
        )
    return LeadResponse.model_validate(lead)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un lead (soft delete)",
    dependencies=[Depends(require_api_key)],
)
async def delete_lead(
    lead_id: int,
    service: LeadService = Depends(get_lead_service),
) -> None:
    """Marca el lead como eliminado. No lo borra de la BD."""
    deleted = await service.delete_lead(lead_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead con id {lead_id} no encontrado",
        )


@router.get(
    "/{lead_id}/events",
    response_model=list[LeadEventResponse],
    summary="Historial de eventos de un lead",
)
async def get_lead_events(
    lead_id: int,
    service: LeadService = Depends(get_lead_service),
) -> list[LeadEventResponse]:
    """Devuelve el timeline completo de un lead."""
    # Verificar que el lead existe
    lead = await service.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead con id {lead_id} no encontrado",
        )
    events = await service.get_lead_events(lead_id)
    return [LeadEventResponse.model_validate(e) for e in events]