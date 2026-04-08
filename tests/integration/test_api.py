"""
Integration Tests for the Finance API endpoints.
Verifies essential flows, CRUD operations, RBAC enforcement, and IDOR protection.
"""

import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Test login with wrong credentials."""
    response = await client.post("/api/v1/auth/login", data={
        "username": "wrong@finance.dev",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["message"]


@pytest.mark.asyncio
async def test_admin_get_users(client, admin_headers):
    """Test admin can list users."""
    response = await client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    # Unwrap from ResponseWrapper
    payload = response.json()
    assert payload["status"] == "success"
    data = payload["data"]
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1  # The admin user from fixture


@pytest.mark.asyncio
async def test_idempotent_record_creation(client, admin_headers):
    """Repeated POST with same Idempotency-Key returns same record without duplicates."""
    record_payload = {
        "amount": 123.45,
        "type": "income",
        "category": "IdemTest",
        "date": "2025-02-02",
        "notes": "First post"
    }
    headers = {**admin_headers, "Idempotency-Key": "idem-key-1"}

    first = await client.post("/api/v1/records", json=record_payload, headers=headers)
    assert first.status_code == 201
    first_id = first.json()["data"]["id"]

    second = await client.post("/api/v1/records", json=record_payload, headers=headers)
    assert second.status_code == 201
    second_id = second.json()["data"]["id"]

    assert first_id == second_id


@pytest.mark.asyncio
async def test_idempotent_conflict_on_payload_change(client, admin_headers):
    """Reusing the same Idempotency-Key with different payload yields 409."""
    headers = {**admin_headers, "Idempotency-Key": "idem-key-2"}

    base_payload = {
        "amount": 200.00,
        "type": "income",
        "category": "Base",
        "date": "2025-03-03",
        "notes": "Base payload"
    }
    alt_payload = {**base_payload, "amount": 250.00}

    first = await client.post("/api/v1/records", json=base_payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/api/v1/records", json=alt_payload, headers=headers)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_admin_create_and_summary_record(client, admin_headers):
    """Test admin can create a record and it appears in summary."""
    # Create income record
    record_payload = {
        "amount": 1500.50,
        "type": "income",
        "category": "Salary",
        "date": "2025-01-15",
        "notes": "Test salary"
    }
    response = await client.post(
        "/api/v1/records",
        json=record_payload,
        headers={**admin_headers, "Idempotency-Key": "test-create-1"},
    )
    assert response.status_code == 201
    
    # Unwrap creation response
    creation_payload = response.json()
    assert creation_payload["status"] == "success"
    record_data = creation_payload["data"]
    assert record_data["amount"] == 1500.50
    assert record_data["type"] == "income"

    # Fetch summary
    response_summary = await client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert response_summary.status_code == 200
    
    # Unwrap summary response
    summary_payload = response_summary.json()
    assert summary_payload["status"] == "success"
    summary_data = summary_payload["data"]

    assert summary_data["total_income"] == 1500.50
    assert summary_data["record_count"] == 1


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Test protected endpoints return 401 without token."""
    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


# --- IDOR SECURITY TESTS ---

@pytest.mark.asyncio
async def test_viewer_cannot_see_admin_records(client, admin_headers, viewer_headers):
    """
    SECURITY TEST: Verify that a viewer cannot access records created by admin.
    """
    # Admin creates a record
    record_payload = {
        "amount": 9999.99,
        "type": "income",
        "category": "Admin Secret",
        "date": "2025-06-01",
        "notes": "Confidential admin record"
    }
    create_response = await client.post(
        "/api/v1/records",
        json=record_payload,
        headers={**admin_headers, "Idempotency-Key": "test-admin-secret"},
    )
    assert create_response.status_code == 201
    admin_record_id = create_response.json()["data"]["id"]

    # Viewer tries to access admin's record by UUID — should get 404 (not 403)
    viewer_response = await client.get(f"/api/v1/records/{admin_record_id}", headers=viewer_headers)
    assert viewer_response.status_code == 404


@pytest.mark.asyncio
async def test_viewer_sees_only_own_records_in_list(client, admin_headers, viewer_headers):
    """
    SECURITY TEST: Verify viewer's record list doesn't include admin's records.
    """
    # Admin creates a record
    await client.post(
        "/api/v1/records",
        json={
            "amount": 5000.00, "type": "expense", "category": "Admin Only",
            "date": "2025-07-01", "notes": "Should not appear for viewer"
        },
        headers={**admin_headers, "Idempotency-Key": "test-admin-only"},
    )

    # Viewer lists their records — should see 0 (they haven't created any)
    viewer_list = await client.get("/api/v1/records", headers=viewer_headers)
    assert viewer_list.status_code == 200
    assert viewer_list.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_viewer_summary_is_scoped(client, admin_headers, viewer_headers):
    """
    SECURITY TEST: Verify viewer's dashboard summary only reflects their own data.
    """
    # Admin creates a 10000 income record
    await client.post(
        "/api/v1/records",
        json={
            "amount": 10000.00, "type": "income", "category": "Admin Revenue",
            "date": "2025-08-01", "notes": "Admin only income"
        },
        headers={**admin_headers, "Idempotency-Key": "test-admin-revenue"},
    )

    # Viewer's summary should show 0 income (they have no records)
    viewer_summary = await client.get("/api/v1/dashboard/summary", headers=viewer_headers)
    assert viewer_summary.status_code == 200
    
    summary_data = viewer_summary.json()["data"]
    assert summary_data["total_income"] == 0.0
    assert summary_data["record_count"] == 0
