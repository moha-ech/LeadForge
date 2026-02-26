"""
Servicio de leads: toda la lógica de negocio.

Los endpoints llaman a este servicio, nunca tocan la BD directamente.
Así la lógica es reutilizable desde Celery, tests, o cualquier otro sitio.
"""

import logging
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import (
    Company,
    EventType,
    Lead,
    LeadEvent,
    LeadStatus,
)
from app.schemas.lead import LeadCreate, LeadUpdate

logger = logging.getLogger(__name__)


class LeadService:
    """Operaciones de negocio sobre leads."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------
    # Crear
    # ------------------------------------------

    async def create_lead(self, data: LeadCreate) -> Lead:
        """
        Crea un lead nuevo con su empresa asociada.

        1. Comprueba si el email ya existe (duplicado)
        2. Busca o crea la empresa por dominio del email
        3. Crea el lead
        4. Registra evento de creación
        """
        # Comprobar duplicado
        existing = await self._get_lead_by_email(data.email)
        if existing:
            raise LeadAlreadyExistsError(data.email)

        # Buscar o crear empresa
        domain = self._extract_domain(data.email)
        company = await self._get_or_create_company(domain, data.company_name)

        # Crear lead
        lead = Lead(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            job_title=data.job_title,
            source=data.source,
            status=LeadStatus.NEW,
            notes=data.notes,
            company_id=company.id if company else None,
        )
        self.db.add(lead)
        await self.db.flush()  # Genera el ID sin hacer commit

        # Registrar evento
        event = LeadEvent(
            lead_id=lead.id,
            event_type=EventType.CREATED,
            event_data={"source": data.source.value},
            created_by="system",
        )
        self.db.add(event)
        await self.db.flush()

        # Cargar la empresa asociada al lead
        await self.db.refresh(lead, ["company"])

        logger.info(
            "Lead creado: %s (%s) - empresa: %s",
            lead.full_name,
            lead.email,
            company.domain if company else "N/A",
        )

        return lead

    # ------------------------------------------
    # Leer
    # ------------------------------------------

    async def get_lead(self, lead_id: int) -> Lead | None:
        """Obtiene un lead por ID con su empresa cargada."""
        query = (
            select(Lead)
            .options(selectinload(Lead.company))
            .where(Lead.id == lead_id, Lead.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        page: int = 1,
        size: int = 20,
        status: LeadStatus | None = None,
        source: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Lead], int]:
        """
        Lista leads con filtros y paginación.

        Devuelve (leads, total) para construir la respuesta paginada.
        """
        query = (
            select(Lead)
            .options(selectinload(Lead.company))
            .where(Lead.deleted_at.is_(None))
        )
        count_query = select(func.count(Lead.id)).where(
            Lead.deleted_at.is_(None)
        )

        # Filtros
        if status:
            query = query.where(Lead.status == status)
            count_query = count_query.where(Lead.status == status)
        if source:
            query = query.where(Lead.source == source)
            count_query = count_query.where(Lead.source == source)
        if search:
            search_filter = Lead.full_name.ilike(f"%{search}%") | Lead.email.ilike(
                f"%{search}%"
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Paginación y orden
        query = (
            query.order_by(Lead.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.db.execute(query)
        leads = list(result.scalars().all())

        return leads, total

    async def get_lead_events(self, lead_id: int) -> list[LeadEvent]:
        """Obtiene el historial de eventos de un lead."""
        query = (
            select(LeadEvent)
            .where(LeadEvent.lead_id == lead_id)
            .order_by(LeadEvent.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------
    # Actualizar
    # ------------------------------------------

    async def update_lead(
        self, lead_id: int, data: LeadUpdate
    ) -> Lead | None:
        """Actualiza los campos proporcionados de un lead."""
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        # Solo actualiza campos que vienen en el request
        update_data = data.model_dump(exclude_unset=True)
        old_status = lead.status

        for field, value in update_data.items():
            setattr(lead, field, value)

        # Si cambió el estado, registrar evento
        if "status" in update_data and data.status != old_status:
            event = LeadEvent(
                lead_id=lead.id,
                event_type=EventType.STATUS_CHANGED,
                event_data={
                    "from": old_status.value,
                    "to": data.status.value,
                },
                created_by="system",
            )
            self.db.add(event)

        logger.info("Lead actualizado: %s (campos: %s)", lead_id, list(update_data.keys()))
        return lead

    # ------------------------------------------
    # Eliminar (soft delete)
    # ------------------------------------------

    async def delete_lead(self, lead_id: int) -> bool:
        """Soft delete: marca el lead como eliminado sin borrarlo."""
        lead = await self.get_lead(lead_id)
        if not lead:
            return False

        lead.deleted_at = func.now()
        logger.info("Lead eliminado (soft): %s", lead_id)
        return True

    # ------------------------------------------
    # Helpers privados
    # ------------------------------------------

    async def _get_lead_by_email(self, email: str) -> Lead | None:
        """Busca un lead por email (para deduplicación)."""
        query = select(Lead).where(
            Lead.email == email, Lead.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _extract_domain(self, email: str) -> str:
        """Extrae el dominio de un email: juan@acme.com → acme.com"""
        return email.split("@")[1].lower()

    async def _get_or_create_company(
        self, domain: str, name: str | None = None
    ) -> Company | None:
        """
        Busca una empresa por dominio o la crea si no existe.

        Dominios genéricos (gmail, hotmail...) no crean empresa.
        """
        generic_domains = {
            "gmail.com", "hotmail.com", "outlook.com", "yahoo.com",
            "icloud.com", "protonmail.com", "live.com", "msn.com",
        }
        if domain in generic_domains:
            return None

        # Buscar existente
        query = select(Company).where(Company.domain == domain)
        result = await self.db.execute(query)
        company = result.scalar_one_or_none()

        if company:
            return company

        # Crear nueva
        company = Company(
            name=name or domain.split(".")[0].capitalize(),
            domain=domain,
        )
        self.db.add(company)
        await self.db.flush()

        logger.info("Empresa creada: %s (%s)", company.name, company.domain)
        return company


# ------------------------------------------
# Excepciones de negocio
# ------------------------------------------


class LeadAlreadyExistsError(Exception):
    """Se lanza cuando intentas crear un lead con un email que ya existe."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Ya existe un lead con email: {email}")