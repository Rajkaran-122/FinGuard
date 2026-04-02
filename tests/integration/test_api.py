"""
Basic Integration Tests for the Finance API endpoints.
Verifies essential flows, CRUD operations, and RBAC enforcement.
"""

def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_invalid_credentials(client):
    """Test login with wrong credentials."""
    response = client.post("/api/auth/login", data={
        "username": "wrong@finance.dev",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_admin_get_users(client, admin_headers):
    """Test admin can list users."""
    response = client.get("/api/users/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1  # The admin user from fixture


def test_admin_create_and_summary_record(client, admin_headers):
    """Test admin can create a record and it appears in summary."""
    # Create income record
    record_payload = {
        "amount": 1500.50,
        "type": "income",
        "category": "Salary",
        "date": "2025-01-15",
        "notes": "Test salary"
    }
    response = client.post("/api/records/", json=record_payload, headers=admin_headers)
    assert response.status_code == 201
    record_data = response.json()
    assert record_data["amount"] == 1500.50
    assert record_data["type"] == "income"

    # Fetch summary
    response_summary = client.get("/api/dashboard/summary", headers=admin_headers)
    assert response_summary.status_code == 200
    summary_data = response_summary.json()
    
    assert summary_data["total_income"] == 1500.50
    assert summary_data["record_count"] == 1


def test_unauthorized_access(client):
    """Test protected endpoints return 401 without token."""
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401
