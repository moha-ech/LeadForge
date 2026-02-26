"""
Servicio de caché con Redis.

Patrón cache-aside: antes de hacer una operación costosa,
mira si el resultado ya está en caché. Si está, devuélvelo.
Si no, ejecuta la operación, guarda el resultado, y devuélvelo.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cliente Redis async (singleton)
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Obtiene el cliente Redis (lo crea si no existe)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


class CacheService:
    """Operaciones de caché sobre Redis."""

    # TTL por defecto: 24 horas
    DEFAULT_TTL = 86400

    # Prefijos para organizar las keys
    PREFIX_ENRICHMENT = "enrich"
    PREFIX_DOMAIN = "domain"

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    def _make_key(self, prefix: str, identifier: str) -> str:
        """Genera una key con formato consistente: leadforge:{prefix}:{id}"""
        return f"leadforge:{prefix}:{identifier}"

    async def get(self, prefix: str, identifier: str) -> dict[str, Any] | None:
        """Busca un valor en caché. Devuelve None si no existe o expiró."""
        key = self._make_key(prefix, identifier)
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug("Cache HIT: %s", key)
                return json.loads(data)
            logger.debug("Cache MISS: %s", key)
            return None
        except Exception as e:
            logger.error("Error leyendo caché %s: %s", key, e)
            return None

    async def set(
        self, prefix: str, identifier: str, data: dict[str, Any], ttl: int | None = None,
    ) -> None:
        """Guarda un valor en caché con TTL."""
        key = self._make_key(prefix, identifier)
        try:
            await self.redis.set(
                key,
                json.dumps(data, default=str),
                ex=ttl or self.DEFAULT_TTL,
            )
            logger.debug("Cache SET: %s (TTL: %ss)", key, ttl or self.DEFAULT_TTL)
        except Exception as e:
            logger.error("Error escribiendo caché %s: %s", key, e)

    async def delete(self, prefix: str, identifier: str) -> None:
        """Elimina un valor de caché."""
        key = self._make_key(prefix, identifier)
        try:
            await self.redis.delete(key)
            logger.debug("Cache DELETE: %s", key)
        except Exception as e:
            logger.error("Error eliminando caché %s: %s", key, e)

    async def get_enrichment(self, domain: str) -> dict[str, Any] | None:
        """Busca datos de enriquecimiento cacheados para un dominio."""
        return await self.get(self.PREFIX_ENRICHMENT, domain)

    async def set_enrichment(self, domain: str, data: dict[str, Any]) -> None:
        """Cachea datos de enriquecimiento de un dominio (TTL: 7 días)."""
        await self.set(self.PREFIX_ENRICHMENT, domain, data, ttl=604800)