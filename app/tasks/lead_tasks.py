"""
Tareas Celery para procesamiento de leads.

Cada tarea es un paso del pipeline que se ejecuta en background.
Las tareas se encadenan: enriquecer → puntuar → asignar → notificar.

Todas las tareas son IDEMPOTENTES: ejecutarlas 2 veces
produce el mismo resultado (importante para reintentos).
"""

import logging

from celery import chain

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# --- Tarea principal: lanza el pipeline completo ---


@celery_app.task(bind=True, name="process_new_lead")
def process_new_lead(self, lead_id: int) -> dict:
    """
    Lanza el pipeline completo para un lead nuevo.

    Encadena las tareas en secuencia:
    enriquecer → puntuar → asignar → notificar.
    
    bind=True nos da acceso a 'self' para info de la tarea
    (id, retries, etc.)
    """
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
    """
    Enriquece un lead con datos de APIs externas.

    Por ahora es un esqueleto — lo implementamos en la Fase 3.
    Devuelve el lead_id para que la siguiente tarea lo reciba.
    """
    logger.info("🔍 Enriqueciendo lead %s (intento %s)", lead_id, self.request.retries + 1)

    try:
        # TO DO: Fase 3: llamar APIs de enriquecimiento
        # - Extraer dominio del email
        # - Buscar datos de empresa (Clearbit, Hunter.io)
        # - Scraping del dominio web
        # - Guardar enrichment_data en la BD
        logger.info("✅ Lead %s enriquecido", lead_id)
    except Exception as exc:
        logger.error("❌ Error enriqueciendo lead %s: %s", lead_id, exc)
        # Reintenta con backoff exponencial: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    return lead_id


# --- Paso 2: Scoring ---


@celery_app.task(
    bind=True,
    name="score_lead",
    max_retries=2,
    default_retry_delay=30,
)
def score_lead(self, lead_id: int) -> int:
    """
    Calcula el score de un lead basado en reglas e IA.

    Por ahora es un esqueleto — lo implementamos en la Fase 4.
    """
    logger.info("📊 Puntuando lead %s", lead_id)

    try:
        # TO DO: Fase 4: scoring
        # - Aplicar reglas (email corporativo, tamaño empresa, etc.)
        # - Llamar a Claude API para scoring IA
        # - Combinar scores y guardar breakdown
        # - Actualizar status a SCORED
        logger.info("✅ Lead %s puntuado", lead_id)
    except Exception as exc:
        logger.error("❌ Error puntuando lead %s: %s", lead_id, exc)
        raise self.retry(exc=exc)

    return lead_id


# --- Paso 3: Asignación ---


@celery_app.task(bind=True, name="assign_lead")
def assign_lead(self, lead_id: int) -> int:
    """
    Asigna el lead al vendedor más adecuado.

    Por ahora es un esqueleto — lo implementamos en la Fase 8.
    """
    logger.info("👤 Asignando lead %s", lead_id)

    # TO DO: Fase 8: lógica de asignación
    # - Round-robin entre vendedores
    # - Respetar especialidad y capacidad
    # - Actualizar status a ASSIGNED
    logger.info("✅ Lead %s asignado", lead_id)

    return lead_id


# --- Paso 4: Notificación ---


@celery_app.task(bind=True, name="notify_new_lead")
def notify_new_lead(self, lead_id: int) -> dict:
    """
    Notifica al vendedor asignado sobre el nuevo lead.

    Por ahora es un esqueleto — lo implementamos en la Fase 5 con n8n.
    """
    logger.info("🔔 Notificando sobre lead %s", lead_id)

    # TO DO: Fase 5: notificaciones vía n8n
    # - Llamar webhook de n8n
    # - n8n envía notificación por Slack/email/Telegram
    logger.info("✅ Notificación enviada para lead %s", lead_id)

    return {"status": "notified", "lead_id": lead_id}