"""Servicio orquestador de enriquecimiento.

Ejecuta todos los proveedores en orden, acumula resultados,
y devuelve un diccionario consolidado con todos los datos.
Usa Redis para cachear resultados por dominio.
"""

import logging
from typing import Any

from app.services.cache import CacheService, get_redis
from app.services.enrichment.base import EnrichmentProvider, EnrichmentResult
from app.services.enrichment.providers import (
    GENERIC_DOMAINS,
    DnsProvider,
    EmailAnalysisProvider,
    WebScrapingProvider,
)

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Orquesta la ejecución de múltiples proveedores de enriquecimiento."""

    def __init__(self) -> None:
        self.providers: list[EnrichmentProvider] = [
            EmailAnalysisProvider(),
            WebScrapingProvider(),
            DnsProvider(),
        ]

    async def enrich(self, email: str) -> dict[str, Any]:
        """Ejecuta todos los proveedores y consolida los resultados.

        Primero comprueba si hay datos cacheados para el dominio.
        Si los hay, los reutiliza y solo ejecuta el análisis de email.
        """
        domain = email.split("@")[1].lower()

        # Intentar obtener datos del caché
        if domain not in GENERIC_DOMAINS:
            cache = await self._get_cache()
            if cache:
                cached_data = await cache.get_enrichment(domain)
                if cached_data:
                    logger.info("♻️ Usando datos cacheados para dominio: %s", domain)
                    return await self._enrich_with_cache(email, domain, cached_data)

        # Sin caché: ejecutar todos los proveedores
        result = await self._enrich_full(email, domain)

        # Guardar en caché si el dominio no es genérico
        if domain not in GENERIC_DOMAINS:
            cache = await self._get_cache()
            if cache:
                await cache.set_enrichment(domain, result)
                logger.info("💾 Datos cacheados para dominio: %s", domain)

        return result

    async def _enrich_full(self, email: str, domain: str) -> dict[str, Any]:
        """Ejecuta todos los proveedores (sin caché)."""
        consolidated: dict[str, Any] = {}
        provider_results: list[dict[str, Any]] = []
        success_count = 0

        for provider in self.providers:
            logger.info("Ejecutando proveedor: %s", provider.name)

            result: EnrichmentResult = await provider.safe_enrich(
                email=email, domain=domain, current_data=consolidated,
            )

            provider_results.append({
                "provider": result.provider,
                "success": result.success,
                "data": result.data,
                "error": result.error,
            })

            if result.success:
                consolidated.update(result.data)
                success_count += 1

            logger.info(
                "Proveedor %s: %s",
                provider.name,
                "✅" if result.success else f"❌ {result.error}",
            )

        return {
            "provider_results": provider_results,
            "consolidated": consolidated,
            "stats": {
                "total_providers": len(self.providers),
                "successful": success_count,
                "failed": len(self.providers) - success_count,
            },
            "from_cache": False,
        }

    async def _enrich_with_cache(
        self, email: str, domain: str, cached_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Usa datos cacheados pero ejecuta EmailAnalysisProvider (es específico por email)."""
        email_provider = EmailAnalysisProvider()
        email_result = await email_provider.safe_enrich(
            email=email, domain=domain, current_data={},
        )

        # Combinar: datos de email frescos + datos de dominio cacheados
        consolidated = dict(cached_data.get("consolidated", {}))
        if email_result.success:
            consolidated.update(email_result.data)

        return {
            "provider_results": cached_data.get("provider_results", []),
            "consolidated": consolidated,
            "stats": cached_data.get("stats", {}),
            "from_cache": True,
        }

    async def _get_cache(self) -> CacheService | None:
        """Intenta obtener el servicio de caché. Si Redis no está disponible, devuelve None."""
        try:
            redis = await get_redis()
            return CacheService(redis)
        except Exception as e:
            logger.warning("Redis no disponible, sin caché: %s", e)
            return None