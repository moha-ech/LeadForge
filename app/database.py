"""
Configuración de la base de datos con SQLAlchemy async.

Define el engine, la sesión y la dependencia de FastAPI
para inyectar sesiones en los endpoints.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI que provee una sesión de DB.

    Uso en un endpoint:
        @router.get("/leads")
        async def list_leads(db: AsyncSession = Depends(get_db)):
            ...

    El 'yield' asegura que la sesión se cierra siempre,
    incluso si hay un error en el endpoint.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
