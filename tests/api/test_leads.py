"""
Tests para los endpoints de leads.

Naming convention: test_<acción>_<escenario>_<resultado>
Cada test es independiente y no depende de otros.
"""

import pytest
from httpx import AsyncClient


# ============================================
# POST /api/v1/leads — Crear lead
# ============================================


class TestCreateLead:
    """Tests para la creación de leads."""

    async def test_create_lead_success(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Crear un lead válido devuelve 201 con los datos correctos."""
        response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["full_name"] == "Test User"
        assert data["email"] == "test@testcompany.com"
        assert data["status"] == "new"
        assert data["score"] is None
        assert data["company"] is not None
        assert data["company"]["domain"] == "testcompany.com"

    async def test_create_lead_gmail_no_company(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_gmail: dict,
    ) -> None:
        """Lead con email genérico no crea empresa."""
        response = await client.post(
            "/api/v1/leads",
            json=sample_lead_gmail,
            headers=api_key_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["company"] is None

    async def test_create_lead_duplicate_email_returns_409(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Intentar crear un lead con email duplicado devuelve 409."""
        # Crear el primero
        await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        # Intentar crear duplicado
        response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        assert response.status_code == 409

    async def test_create_lead_without_api_key_returns_401(
        self,
        client: AsyncClient,
        sample_lead_data: dict,
    ) -> None:
        """Crear lead sin API Key devuelve 401."""
        response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
        )
        assert response.status_code == 401

    async def test_create_lead_invalid_api_key_returns_401(
        self,
        client: AsyncClient,
        sample_lead_data: dict,
    ) -> None:
        """Crear lead con API Key inválida devuelve 401."""
        response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers={"X-API-Key": "fake-key-12345"},
        )
        assert response.status_code == 401

    async def test_create_lead_invalid_email_returns_422(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """Email inválido devuelve 422 (validation error)."""
        response = await client.post(
            "/api/v1/leads",
            json={
                "full_name": "Bad Email",
                "email": "not-an-email",
                "source": "form",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 422

    async def test_create_lead_missing_required_fields_returns_422(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """Faltar campos obligatorios devuelve 422."""
        response = await client.post(
            "/api/v1/leads",
            json={"full_name": "Only Name"},
            headers=api_key_headers,
        )
        assert response.status_code == 422

    async def test_create_lead_email_normalized_to_lowercase(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """El email se normaliza a minúsculas."""
        response = await client.post(
            "/api/v1/leads",
            json={
                "full_name": "Upper Case",
                "email": "UPPER@TestDomain.COM",
                "source": "form",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 201
        assert response.json()["email"] == "upper@testdomain.com"


# ============================================
# GET /api/v1/leads — Listar leads
# ============================================


class TestListLeads:
    """Tests para el listado de leads."""

    async def test_list_leads_empty(
        self,
        client: AsyncClient,
    ) -> None:
        """Listar sin leads devuelve lista vacía."""
        response = await client.get("/api/v1/leads")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_leads_returns_created_lead(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Después de crear un lead, aparece en el listado."""
        await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )

        response = await client.get("/api/v1/leads")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "test@testcompany.com"

    async def test_list_leads_pagination(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """La paginación limita resultados correctamente."""
        # Crear 3 leads
        for i in range(3):
            await client.post(
                "/api/v1/leads",
                json={
                    "full_name": f"User {i}",
                    "email": f"user{i}@company{i}.com",
                    "source": "form",
                },
                headers=api_key_headers,
            )

        # Pedir página 1 con tamaño 2
        response = await client.get("/api/v1/leads?page=1&size=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["pages"] == 2


# ============================================
# GET /api/v1/leads/{id} — Detalle
# ============================================


class TestGetLead:
    """Tests para obtener detalle de un lead."""

    async def test_get_lead_success(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Obtener un lead existente devuelve 200."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/leads/{lead_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "test@testcompany.com"

    async def test_get_lead_not_found_returns_404(
        self,
        client: AsyncClient,
    ) -> None:
        """Pedir un lead que no existe devuelve 404."""
        response = await client.get("/api/v1/leads/99999")
        assert response.status_code == 404


# ============================================
# PATCH /api/v1/leads/{id} — Actualizar
# ============================================


class TestUpdateLead:
    """Tests para actualizar leads."""

    async def test_update_lead_success(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Actualizar campos de un lead funciona correctamente."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"job_title": "Senior Developer", "phone": "+34 999 999 999"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["job_title"] == "Senior Developer"
        assert response.json()["phone"] == "+34 999 999 999"
        # El nombre no debe cambiar
        assert response.json()["full_name"] == "Test User"

    async def test_update_lead_status_change(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Cambiar el estado de un lead se refleja correctamente."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"status": "contacted"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "contacted"

    async def test_update_lead_status_creates_event(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Cambiar el estado genera un evento status_changed."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        await client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"status": "scored"},
            headers=api_key_headers,
        )

        events_response = await client.get(f"/api/v1/leads/{lead_id}/events")
        events = events_response.json()
        status_events = [e for e in events if e["event_type"] == "status_changed"]
        assert len(status_events) == 1
        assert status_events[0]["event_data"]["from"] == "new"
        assert status_events[0]["event_data"]["to"] == "scored"

    async def test_update_lead_not_found_returns_404(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """Actualizar un lead que no existe devuelve 404."""
        response = await client.patch(
            "/api/v1/leads/99999",
            json={"notes": "algo"},
            headers=api_key_headers,
        )
        assert response.status_code == 404

    async def test_update_lead_without_api_key_returns_401(
        self,
        client: AsyncClient,
        sample_lead_data: dict,
        api_key_headers: dict,
    ) -> None:
        """Actualizar sin API Key devuelve 401."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"notes": "sin auth"},
        )
        assert response.status_code == 401

    async def test_update_lead_partial_only_changes_sent_fields(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """PATCH solo modifica los campos enviados, el resto no cambia."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]
        original = create_response.json()

        response = await client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"notes": "nota nueva"},
            headers=api_key_headers,
        )
        updated = response.json()

        assert updated["notes"] == "nota nueva"
        assert updated["full_name"] == original["full_name"]
        assert updated["phone"] == original["phone"]
        assert updated["job_title"] == original["job_title"]
        assert updated["status"] == original["status"]


# ============================================
# DELETE /api/v1/leads/{id} — Soft delete
# ============================================


class TestDeleteLead:
    """Tests para eliminar leads."""

    async def test_delete_lead_success(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Eliminar un lead devuelve 204 y ya no aparece en listado."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        # Eliminar
        response = await client.delete(
            f"/api/v1/leads/{lead_id}",
            headers=api_key_headers,
        )
        assert response.status_code == 204

        # Ya no aparece en GET
        response = await client.get(f"/api/v1/leads/{lead_id}")
        assert response.status_code == 404

    async def test_delete_lead_not_found_returns_404(
        self,
        client: AsyncClient,
        api_key_headers: dict,
    ) -> None:
        """Eliminar un lead que no existe devuelve 404."""
        response = await client.delete(
            "/api/v1/leads/99999",
            headers=api_key_headers,
        )
        assert response.status_code == 404


# ============================================
# GET /api/v1/leads/{id}/events — Historial
# ============================================


class TestLeadEvents:
    """Tests para el historial de eventos."""

    async def test_lead_has_created_event(
        self,
        client: AsyncClient,
        api_key_headers: dict,
        sample_lead_data: dict,
    ) -> None:
        """Un lead recién creado tiene un evento 'created'."""
        create_response = await client.post(
            "/api/v1/leads",
            json=sample_lead_data,
            headers=api_key_headers,
        )
        lead_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/leads/{lead_id}/events")
        assert response.status_code == 200

        events = response.json()
        assert len(events) >= 1
        assert any(e["event_type"] == "created" for e in events)