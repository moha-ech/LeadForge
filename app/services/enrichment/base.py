"""
Interfaz base para proveedores de enriquecimiento.

Todos los proveedores implementan el mismo contrato.
Así puedes añadir/quitar proveedores sin tocar el pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import logging

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """
    Resultado de un proveedor de enriquecimiento.
    
    - provider: nombre del proveedor que generó los datos
    - success: si la operación fue exitosa
    - data: diccionario con los datos obtenidos
    - error: mensaje de error si falló
    """
    provider: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class EnrichmentProvider(ABC):
    """Interfaz que todos los proveedores deben implementar."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único del proveedor."""
        ...

    @abstractmethod
    async def enrich(self, email: str, domain: str, current_data: dict[str, Any]) -> EnrichmentResult:
        """
        Ejecuta el enriquecimiento.

        Args:
            email: email del lead
            domain: dominio extraído del email
            current_data: datos acumulados por proveedores anteriores
                         (útil para no repetir trabajo)
        
        Returns:
            EnrichmentResult con los datos obtenidos o el error
        """
        ...

    async def safe_enrich(self, email: str, domain: str, current_data: dict[str, Any]) -> EnrichmentResult:
        """
        Wrapper que captura cualquier excepción.
        
        Así un proveedor que falla no rompe todo el pipeline.
        """
        try:
            return await self.enrich(email, domain, current_data)
        except Exception as e:
            logger.error("Error en proveedor %s: %s", self.name, e)
            return EnrichmentResult(
                provider=self.name,
                success=False,
                error=str(e),
            )