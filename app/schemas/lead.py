"""
Schemas Pydantic para leads y empresas.

Definen qué datos acepta la API (input) y qué devuelve (output).
Pydantic valida automáticamente: si alguien envía un email
sin @, la API rechaza el request antes de tocar la base de datos.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.lead import (
    CompanySize,
    EventType,
    LeadSource,
    LeadStatus,
)

# ============================================
# Company Schemas
# ============================================


class CompanyBase(BaseModel):
    """Campos comunes de empresa."""
    name: str = Field(..., min_length=1, max_length=255, examples=["Acme Corp"])
    domain: str = Field(..., min_length=3, max_length=255, examples=["acme.com"])
    industry: str | None = Field(None, max_length=100, examples=["technology"])
    size: CompanySize = CompanySize.UNKNOWN
    country: str | None = Field(None, max_length=100, examples=["Spain"])
    website_url: str | None = Field(None, max_length=500, examples=["https://acme.com"])


class CompanyResponse(CompanyBase):
    """Lo que la API devuelve al consultar una empresa."""
    id: int
    enrichment_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================
# Lead Schemas
# ============================================


class LeadCreate(BaseModel):
    """
    Datos necesarios para crear un lead.
    
    Solo pedimos lo mínimo: nombre, email y fuente.
    El resto es opcional porque el enriquecimiento lo completará.
    """
    full_name: str = Field(
        ..., min_length=1, max_length=255, examples=["Juan García"]
    )
    email: EmailStr = Field(..., examples=["juan@acme.com"])
    phone: str | None = Field(None, max_length=50, examples=["+34 612 345 678"])
    job_title: str | None = Field(None, max_length=255, examples=["CTO"])
    source: LeadSource = Field(..., examples=["form"])
    notes: str | None = None

    # Datos de empresa (opcionales: si no los envían,
    # intentamos crear la empresa desde el dominio del email)
    company_name: str | None = Field(None, max_length=255, examples=["Acme Corp"])

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normaliza el email a minúsculas para evitar duplicados."""
        return v.lower().strip()

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Limpia espacios extra del nombre."""
        return " ".join(v.split()).strip()


class LeadUpdate(BaseModel):
    """Campos actualizables de un lead. Todos opcionales."""
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=50)
    job_title: str | None = Field(None, max_length=255)
    status: LeadStatus | None = None
    notes: str | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        """Limpia espacios extra del nombre."""
        if v is not None:
            return " ".join(v.split()).strip()
        return v


class LeadResponse(BaseModel):
    """Lo que la API devuelve al consultar un lead."""
    id: int
    full_name: str
    email: str
    phone: str | None
    job_title: str | None
    source: LeadSource
    status: LeadStatus
    score: int | None
    score_breakdown: dict | None
    enrichment_data: dict | None = None
    notes: str | None
    first_contacted_at: datetime | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Empresa anidada (si tiene)
    company: CompanyResponse | None = None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    """Respuesta paginada de leads."""
    items: list[LeadResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================
# LeadEvent Schemas
# ============================================


class LeadEventResponse(BaseModel):
    """Un evento del historial de un lead."""
    id: int
    event_type: EventType
    event_data: dict | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}