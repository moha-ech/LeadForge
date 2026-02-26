"""
Fixtures de Pytest para tests de LeadForge.

Estrategia:
- Un solo event loop para toda la sesión de tests (asyncio_default_fixture_loop_scope=session)
- Engine con NullPool: cada operación obtiene una conexión fresca, sin reutilización
- Override de get_db para que la app use el engine de test
- Después de cada test se limpian las tablas con TRUNCATE
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import get_db
from app.main import app


settings = get_settings()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Engine de test con NullPool — conexión fresca por operación."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Factory de sesiones ligada al engine de test."""
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )


@pytest_asyncio.fixture(autouse=True)
async def _setup_db_override(
    test_session_factory: async_sessionmaker[AsyncSession],
    test_engine: AsyncEngine,
) -> AsyncGenerator[None, None]:
    """Override de get_db + limpieza de tablas después de cada test."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

    async with test_engine.connect() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE lead_events, leads, companies "
            "RESTART IDENTITY CASCADE"
        ))
        await conn.commit()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP que habla directamente con la app FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# --- Headers con API Key ---

@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """Headers con una API Key válida."""
    return {"X-API-Key": settings.API_KEYS[0]}


# --- Datos de prueba ---

@pytest.fixture
def sample_lead_data() -> dict:
    """Datos de un lead válido."""
    return {
        "full_name": "Test User",
        "email": "test@testcompany.com",
        "phone": "+34 600 000 000",
        "job_title": "Developer",
        "source": "form",
        "company_name": "Test Company",
    }


@pytest.fixture
def sample_lead_gmail() -> dict:
    """Lead con email genérico (sin empresa)."""
    return {
        "full_name": "Gmail User",
        "email": "testuser@gmail.com",
        "source": "manual",
    }


# --- Mock de Celery ---

@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Desactiva las tareas de Celery en tests."""
    from app.tasks import lead_tasks
    monkeypatch.setattr(
        lead_tasks.process_new_lead, "delay", lambda *args, **kwargs: None,
    )
