import pytest

pytestmark = pytest.mark.api

def test_create_limit_buy_order(test_app, auth_headers):
    response = test_app.post("/api/v1/orders/", json={"bond_id": 1, "side": "BUY", "type": "LIMIT", "price": 95.0, "quantity": 100}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "user_id" in data
    assert data["bond_id"] == 1
    assert data["side"] == "BUY"
    assert data["type"] == "LIMIT"
    assert data["price"] == 95.0
    assert data["quantity"] == 100
    assert "remaining_qty" in data
    assert "status" in data
    assert "bond" in data

def test_create_limit_sell_order(test_app, auth_headers):
    response = test_app.post("/api/v1/orders/", json={"bond_id": 1, "side": "SELL", "type": "LIMIT", "price": 105.0, "quantity": 100}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["side"] == "SELL"
    assert data["price"] == 105.0

def test_create_order_invalid_bond(test_app, auth_headers):
    response = test_app.post("/api/v1/orders/", json={"bond_id": 999, "side": "BUY", "type": "LIMIT", "price": 95.0, "quantity": 100}, headers=auth_headers)
    assert response.status_code == 404

def test_get_orders(test_app, auth_headers):
    test_app.post("/api/v1/orders/", json={"bond_id": 1, "side": "BUY", "type": "LIMIT", "price": 95.0, "quantity": 100}, headers=auth_headers)
    response = test_app.get("/api/v1/orders/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_get_orders_filter_by_status(test_app, auth_headers):
    response = test_app.get("/api/v1/orders/?status=PENDING", headers=auth_headers)
    assert response.status_code == 200
    for order in response.json():
        assert order["status"] == "PENDING"

def test_get_open_orders(test_app, auth_headers):
    response = test_app.get("/api/v1/orders/open", headers=auth_headers)
    assert response.status_code == 200
    for order in response.json():
        assert order["status"] in ["PENDING", "PARTIAL"]

def test_cancel_order(test_app, auth_headers):
    # Place a limit order far away so it stays pending
    res = test_app.post("/api/v1/orders/", json={"bond_id": 1, "side": "BUY", "type": "LIMIT", "price": 80.0, "quantity": 100}, headers=auth_headers)
    order_id = res.json()["id"]
    
    response = test_app.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

def test_create_order_zero_quantity_rejected(test_app, auth_headers):
    """Regression test for BUG-104: Prevents order entry with 0 quantity."""
    response = test_app.post(
        "/api/v1/orders/",
        json={"bond_id": 1, "side": "BUY", "type": "LIMIT", "price": 100.0, "quantity": 0},
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "greater than 0" in str(response.json()) or "Input should be greater than 0" in str(response.json())

def test_create_order_negative_quantity_rejected(test_app, auth_headers):
    """Regression test for BUG-104: Prevents order entry with negative quantity."""
    response = test_app.post(
        "/api/v1/orders/",
        json={"bond_id": 1, "side": "SELL", "type": "LIMIT", "price": 100.0, "quantity": -5000},
        headers=auth_headers
    )
    assert response.status_code == 422
