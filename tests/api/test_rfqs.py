import pytest

pytestmark = pytest.mark.api

def test_create_client_rfq(test_app, auth_headers):
    response = test_app.post("/api/v1/rfqs/", json={"bond_id": 1, "side": "BUY", "quantity": 1000}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "client_id" in data
    assert data["bond_id"] == 1
    assert data["side"] == "BUY"
    assert data["quantity"] == 1000
    assert data["status"] == "REQUESTED"
    assert "expires_at" in data
    assert "bond" in data

def test_get_client_rfqs(test_app, auth_headers):
    test_app.post("/api/v1/rfqs/", json={"bond_id": 1, "side": "BUY", "quantity": 1000}, headers=auth_headers)
    response = test_app.get("/api/v1/rfqs/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_get_rfq_details(test_app, auth_headers):
    res = test_app.post("/api/v1/rfqs/", json={"bond_id": 1, "side": "BUY", "quantity": 1000}, headers=auth_headers)
    rfq_id = res.json()["id"]
    response = test_app.get(f"/api/v1/rfqs/{rfq_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "quotes" in response.json()

def test_get_incoming_rfqs(test_app, auth_headers):
    response = test_app.get("/api/v1/rfqs/incoming", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_incoming_rfqs_history(test_app, auth_headers):
    response = test_app.get("/api/v1/rfqs/incoming/history", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
