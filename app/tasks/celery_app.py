"""
Configuración central de Celery.

Define la app de Celery, la conexión a Redis como broker,
y la configuración general de las tareas.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Crear la app de Celery
# "leadforge" es el nombre que aparece en logs y Flower
celery_app = Celery(
    "leadforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configuración
celery_app.conf.update(
    # Serialización: JSON es más seguro que pickle
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Las tareas se confirman DESPUÉS de ejecutarse, no antes.
    # Si el worker muere a mitad de una tarea, Redis la reencola.
    task_acks_late=True,

    # Un worker solo toma una tarea a la vez.
    # Evita que un worker acapare tareas mientras otros están libres.
    worker_prefetch_multiplier=1,

    # Si el resultado no se recoge en 24h, se borra de Redis.
    result_expires=86400,

    # Autodescubrir tareas en estos módulos
    # Celery busca funciones @celery_app.task en estos archivos
    imports=["app.tasks.lead_tasks"],
)