"""
Modelos de datos para leads, empresas y eventos.

Define las tablas en PostgreSQL mediante SQLAlchemy 2.0.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# --- ENUMS ---

class LeadStatus(str, enum.Enum):
    """Estados del ciclo de vida de un lead."""
    NEW = "new"                  # Acaba de llegar
    ENRICHED = "enriched"        # Datos enriquecidos
    SCORED = "scored"            # Puntuación calculada
    ASSIGNED = "assigned"        # Asignado a vendedor
    CONTACTED = "contacted"      # Se ha contactado
    CONVERTED = "converted"      # Se ha convertido en cliente
    LOST = "lost"                # Se ha perdido


class LeadSource(str, enum.Enum):
    """De dónde vino el lead."""
    FORM = "form"                # Formulario web
    CSV = "csv"                  # Importación masiva
    WEBHOOK = "webhook"          # Sistema externo
    MANUAL = "manual"            # Creado a mano
    API = "api"                  # Vía API directa


class CompanySize(str, enum.Enum):
    """Tamaño de la empresa."""
    STARTUP = "startup"          # 1-10 empleados
    SMB = "smb"                  # 11-50 empleados
    MID_MARKET = "mid_market"    # 51-500 empleados
    ENTERPRISE = "enterprise"    # 500+ empleados
    UNKNOWN = "unknown"


class EventType(str, enum.Enum):
    """Tipos de eventos que pueden ocurrir con un lead."""
    CREATED = "created"
    ENRICHED = "enriched"
    SCORED = "scored"
    ASSIGNED = "assigned"
    CONTACTED = "contacted"
    STATUS_CHANGED = "status_changed"
    NOTE_ADDED = "note_added"
    CONVERTED = "converted"
    LOST = "lost"


# --- MODELS ---

class Company(BaseModel):
    """ 
    Empresa asosciada a uno o mas leads
    
    Se duplica por dominio: si dos leads tienen email
    @meta.com, ambos apuntan a la misma Company
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[CompanySize] = mapped_column(
        Enum(CompanySize), default=CompanySize.UNKNOWN, nullable=False
    )
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relación: una empresa tiene muchos leads
    leads: Mapped[list["Lead"]] = relationship(back_populates="company")

    def __repr__(self) -> str:
        return f"<Company {self.name} ({self.domain})>"


class Lead(BaseModel):
    """
    Lead comercial: una persona interesada en tu producto/servicio.
    
    Se deduplica por email. Siempre pertenece a una empresa
    (que se crea automáticamente a partir del dominio del email).
    """

    __tablename__ = "leads"

    # --- Datos de contacto ---
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Clasificación ---
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource), nullable=False
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.NEW, nullable=False
    )

    # --- Scoring ---
    score: Mapped[int | None] = mapped_column(Integer, nullable=True) # Puntuación del 0-100 (null hasta puntuar)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # JSON con el desglose de porque la anterior nota

    # --- Enriquecimiento ---
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Notas y seguimiento ---
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_contacted_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )
    converted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # --- Relaciones ---
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True # Nulleable porque igual un lead tiene @gmail.com y no pertenece a ninguna empresa
    )
    company: Mapped[Company | None] = relationship(back_populates="leads")

    events: Mapped[list["LeadEvent"]] = relationship(
        back_populates="lead", order_by="LeadEvent.created_at.desc()"
    )

    # --- Índices compuestos ---
    # Esta query devuelve los leads con un status ordenadors por score
    __table_args__ = (
        Index("ix_leads_status_score", "status", "score"),
    )

    def __repr__(self) -> str:
        return f"<Lead {self.full_name} ({self.email})>"


class LeadEvent(BaseModel):
    """
    Registro de algo que ocurrió con un lead.
    
    Forma un timeline completo: creación, enriquecimiento,
    scoring, asignación, contacto, etc.
    """

    __tablename__ = "lead_events"

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id"), nullable=False, index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False
    )
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(100), default="system", nullable=False
    )

    # Relación
    lead: Mapped[Lead] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<LeadEvent {self.event_type.value} for lead {self.lead_id}>"
