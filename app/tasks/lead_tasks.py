"""
Tareas Celery para procesamiento de leads.

Cada tarea es un paso del pipeline que se ejecuta en background.
Las tareas se encadenan: enriquecer → puntuar → asignar → notificar.

NOTA: Celery no soporta async nativo. Usamos asyncio.run()
para ejecutar código async dentro de tareas sync.
"""

import asyncio
import logging

from celery import chain
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.database import async_session
from app.models.lead import EventType, Lead, LeadEvent, LeadStatus

logger = logging.getLogger(__name__)


# --- Helper para ejecutar código async en Celery ---

def run_async(coro):
    """Ejecuta una coroutine async dentro de una tarea sync de Celery."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Helper para obtener un lead de la BD ---

async def _get_lead(session: AsyncSession, lead_id: int) -> Lead | None:
    """Obtiene un lead por ID."""
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


# --- Tarea principal: lanza el pipeline completo ---


@celery_app.task(bind=True, name="process_new_lead")
def process_new_lead(self, lead_id: int) -> dict:
    """Lanza el pipeline completo para un lead nuevo."""
    logger.info("🚀 Iniciando pipeline para lead %s (task: %s)", lead_id, self.request.id)

    pipeline = chain(
        enrich_lead.s(lead_id),
        score_lead.s(),
        assign_lead.s(),
        notify_new_lead.s(),
    )
    pipeline.apply_async()

    return {"status": "pipeline_started", "lead_id": lead_id}


# --- Paso 1: Enriquecimiento ---


@celery_app.task(
    bind=True,
    name="enrich_lead",
    max_retries=3,
    default_retry_delay=60,
)
def enrich_lead(self, lead_id: int) -> int:
    """Enriquece un lead con datos de APIs externas y scraping."""
    logger.info("🔍 Enriqueciendo lead %s (intento %s)", lead_id, self.request.retries + 1)

    try:
        run_async(_do_enrich(lead_id))
        logger.info("✅ Lead %s enriquecido", lead_id)
    except Exception as exc:
        logger.error("❌ Error enriqueciendo lead %s: %s", lead_id, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    return lead_id


async def _do_enrich(lead_id: int) -> None:
    """Lógica async de enriquecimiento."""
    from app.services.enrichment.service import EnrichmentService

    async with async_session() as session:
        lead = await _get_lead(session, lead_id)
        if not lead:
            logger.error("Lead %s no encontrado", lead_id)
            return

        # Ejecutar enriquecimiento
        enrichment_service = EnrichmentService()
        results = await enrichment_service.enrich(lead.email)

        # Guardar datos en el lead
        lead.enrichment_data = results
        lead.status = LeadStatus.ENRICHED

        # Registrar evento
        event = LeadEvent(
            lead_id=lead.id,
            event_type=EventType.ENRICHED,
            event_data={
                "stats": results["stats"],
                "providers_used": [
                    r["provider"] for r in results["provider_results"] if r["success"]
                ],
            },
            created_by="system",
        )
        session.add(event)

        await session.commit()


# --- Paso 2: Scoring ---


@celery_app.task(
    bind=True,
    name="score_lead",
    max_retries=2,
    default_retry_delay=30,
)
def score_lead(self, lead_id: int) -> int:
    """Calcula el score de un lead basado en reglas e IA.

    Por ahora es un esqueleto — lo implementamos en la Fase 4.
    """
    logger.info("📊 Puntuando lead %s", lead_id)

    try:
        # TODO Fase 4: scoring
        logger.info("✅ Lead %s puntuado", lead_id)
    except Exception as exc:
        logger.error("❌ Error puntuando lead %s: %s", lead_id, exc)
        raise self.retry(exc=exc)

    return lead_id


# --- Paso 3: Asignación ---


@celery_app.task(bind=True, name="assign_lead")
def assign_lead(self, lead_id: int) -> int:
    """Asigna el lead al vendedor más adecuado.

    Por ahora es un esqueleto — lo implementamos en la Fase 8.
    """
    logger.info("👤 Asignando lead %s", lead_id)
    logger.info("✅ Lead %s asignado", lead_id)
    return lead_id


# --- Paso 4: Notificación ---


@celery_app.task(bind=True, name="notify_new_lead")
def notify_new_lead(self, lead_id: int) -> dict:
    """Notifica al vendedor asignado sobre el nuevo lead.

    Por ahora es un esqueleto — lo implementamos en la Fase 5 con n8n.
    """
    logger.info("🔔 Notificando sobre lead %s", lead_id)
    logger.info("✅ Notificación enviada para lead %s", lead_id)
    return {"status": "notified", "lead_id": lead_id}