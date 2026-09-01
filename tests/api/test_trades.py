import pytest
from datetime import datetime

pytestmark = pytest.mark.api


def test_get_trades_empty(test_app, auth_headers):
    """Fresh user should have no trades."""
    test_app.post("/api/v1/auth/register", json={"username": "tradeuser1", "password": "password"})
    res = test_app.post("/api/v1/auth/token", data={"username": "tradeuser1", "password": "password"})
    token = res.json()["access_token"]
    new_auth_headers = {"Authorization": f"Bearer {token}"}

    response = test_app.get("/api/v1/trades/", headers=new_auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_trades_after_order_fill(test_app, test_db, auth_headers):
    """
    After placing a LIMIT BUY order that crosses the simulated ask,
    the blotter should show at least one trade.

    We seed a trade directly into the test DB to avoid depending on
    the matching engine's internal session (which may differ from
    the overridden get_db session used by the trades route).
    """
    from backend.app.models import Trade, SettlementStatus, User

    # Look up the test user from the auth_headers fixture
    me_resp = test_app.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_resp.json()["id"]

    # Seed a trade directly
    trade = Trade(
        order_id=None,
        rfq_id=None,
        buyer_id=user_id,
        seller_id=0,
        bond_id=1,
        price=99.85,
        quantity=100,
        principal=100 * 99.85 * (1000.0 / 100.0),  # qty * price * face_value/100
        settlement_status=SettlementStatus.EXECUTED,
        executed_at=datetime.utcnow(),
    )
    test_db.add(trade)
    test_db.commit()

    response = test_app.get("/api/v1/trades/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    trade_entry = data[0]
    expected_fields = ["id", "bond_ticker", "bond_name", "side", "price", "quantity", "principal", "settlement_status"]
    for field in expected_fields:
        assert field in trade_entry

    assert trade_entry["side"] == "BUY"
    assert trade_entry["settlement_status"] == "EXECUTED"


def test_trade_blotter_response_schema(test_app, test_db, auth_headers):
    """Verify blotter entries include all required display fields."""
    from backend.app.models import Trade, SettlementStatus

    me_resp = test_app.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_resp.json()["id"]

    trade = Trade(
        order_id=None,
        rfq_id=None,
        buyer_id=user_id,
        seller_id=0,
        bond_id=1,
        price=99.85,
        quantity=50,
        principal=50 * 99.85 * 10.0,
        settlement_status=SettlementStatus.EXECUTED,
        executed_at=datetime.utcnow(),
    )
    test_db.add(trade)
    test_db.commit()

    response = test_app.get("/api/v1/trades/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    trade_entry = data[0]
    assert "buyer_name" in trade_entry
    assert "seller_name" in trade_entry
    assert "executed_at" in trade_entry
    assert trade_entry["seller_name"] == "STREET_LIQUIDITY"
