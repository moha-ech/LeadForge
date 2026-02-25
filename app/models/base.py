"""
Modelo base de SQLAlchemy con campos comunes.

Todos los modelos del proyecto heredan de BaseModel,
que incluye id, created_at, updated_at y deleted_at.
Así no repites estos campos en cada tabla.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Clase base de SQLAlchemy. Todas las tablas heredan de aquí."""
    pass


class BaseModel(Base):
    """
    Modelo abstracto con campos comunes a todas las tablas.
    
    - id: clave primaria autoincremental
    - created_at: fecha de creación (automática)
    - updated_at: fecha de última actualización (automática)
    - deleted_at: soft delete (None = activo, fecha = eliminado)
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )