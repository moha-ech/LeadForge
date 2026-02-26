"""
Servicio orquestador de enriquecimiento.

Ejecuta todos los proveedores en orden, acumula resultados,
y devuelve un diccionario consolidado con todos los datos.
"""

import logging
from typing import Any

from app.services.enrichment.base import EnrichmentProvider, EnrichmentResult
from app.services.enrichment.providers import (
    DnsProvider,
    EmailAnalysisProvider,
    WebScrapingProvider,
)

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Orquesta la ejecución de múltiples proveedores de enriquecimiento."""

    def __init__(self) -> None:
        # Los proveedores se ejecutan en este orden.
        # Añadir o quitar proveedores es tan fácil como editar esta lista.
        self.providers: list[EnrichmentProvider] = [
            EmailAnalysisProvider(),
            WebScrapingProvider(),
            DnsProvider(),
        ]

    async def enrich(self, email: str) -> dict[str, Any]:
        """
        Ejecuta todos los proveedores y consolida los resultados.

        Args:
            email: email del lead a enriquecer

        Returns:
            Diccionario con:
            - providers_results: resultado de cada proveedor
            - consolidated: datos consolidados de todos los proveedores
            - stats: estadísticas del proceso
        """
        domain = email.split("@")[1].lower()
        consolidated: dict[str, Any] = {}
        provider_results: list[dict[str, Any]] = []
        success_count = 0

        for provider in self.providers:
            logger.info("Ejecutando proveedor: %s", provider.name)

            result: EnrichmentResult = await provider.safe_enrich(
                email=email,
                domain=domain,
                current_data=consolidated,
            )

            # Guardar resultado individual
            provider_results.append({
                "provider": result.provider,
                "success": result.success,
                "data": result.data,
                "error": result.error,
            })

            # Acumular datos exitosos
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
        }