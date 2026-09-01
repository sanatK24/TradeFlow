import pytest

pytestmark = pytest.mark.api

def test_get_all_bonds(test_app, auth_headers):
    response = test_app.get("/api/v1/bonds/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    first_bond = data[0]
    expected_fields = ["id", "isin", "ticker", "name", "coupon", "maturity_date", "type", "face_value", "last_price", "yield_to_maturity"]
    for field in expected_fields:
        assert field in first_bond

def test_get_single_bond(test_app, auth_headers):
    response = test_app.get("/api/v1/bonds/1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["ticker"] == "US02Y"

def test_get_bond_not_found(test_app, auth_headers):
    response = test_app.get("/api/v1/bonds/999", headers=auth_headers)
    assert response.status_code == 404

def test_get_order_book(test_app, auth_headers):
    response = test_app.get("/api/v1/bonds/1/order-book", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "bond_id" in data
    assert "ticker" in data
    assert "last_price" in data
    assert "yield" in data
    assert "bids" in data
    assert "asks" in data
