"""
API Contract Testing Framework

Validates that the live REST API responses strictly adhere to the expected
Pydantic/JSON schemas. This hits the live server via the `requests` library
to ensure end-to-end serialization works precisely as contracted with UI/external clients.
"""

import os
import time
import pytest
import requests
from pydantic import TypeAdapter
from typing import List

# Import Pydantic models (our source of truth for the API contract)
from backend.app.schemas import (
    BondResponse,
    UserResponse,
    OrderResponse,
    TradeBlotterResponse,
    AnalyticsSummary
)

pytestmark = pytest.mark.contract

# Point this to the running dev/staging server
BASE_URL = os.getenv("API_URL", "http://localhost:8001")

@pytest.fixture(scope="module")
def live_auth_session():
    """
    Creates a requests session with a valid JWT token.
    Fails the test suite gracefully if the live server isn't running.
    """
    session = requests.Session()
    username = f"contract_tester_{int(time.time())}"
    password = "StrongPassword123!"
    
    try:
        # Register
        reg_resp = session.post(f"{BASE_URL}/api/v1/auth/register", json={"username": username, "password": password})
        if reg_resp.status_code not in (200, 400):  # 400 means already exists, which is fine
            pytest.skip(f"Live server at {BASE_URL} returned {reg_resp.status_code} on register.")
            
        # Login
        login_resp = session.post(f"{BASE_URL}/api/v1/auth/token", data={"username": username, "password": password})
        if login_resp.status_code != 200:
            pytest.skip(f"Live server at {BASE_URL} failed auth.")
            
        token = login_resp.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    except requests.ConnectionError:
        pytest.skip(f"Live server not running at {BASE_URL}. Skipping contract tests.")


def test_auth_me_contract(live_auth_session):
    """Contract Test: GET /auth/me returns UserResponse schema"""
    response = live_auth_session.get(f"{BASE_URL}/api/v1/auth/me")
    assert response.status_code == 200
    
    # Strict validation against Pydantic schema
    user = UserResponse.model_validate(response.json())
    assert hasattr(user, "id")
    assert hasattr(user, "username")
    assert hasattr(user, "cash_balance")


def test_bonds_contract(live_auth_session):
    """Contract Test: GET /bonds/ returns List[BondResponse] schema"""
    response = live_auth_session.get(f"{BASE_URL}/api/v1/bonds/")
    assert response.status_code == 200
    
    # Strict validation against Pydantic schema
    adapter = TypeAdapter(List[BondResponse])
    bonds = adapter.validate_python(response.json())
    assert len(bonds) > 0
    assert bonds[0].ticker is not None


def test_orders_contract(live_auth_session):
    """Contract Test: POST /orders/ returns OrderResponse schema"""
    payload = {
        "bond_id": 1,
        "side": "BUY",
        "type": "LIMIT",
        "price": 95.50,
        "quantity": 100
    }
    response = live_auth_session.post(f"{BASE_URL}/api/v1/orders/", json=payload)
    assert response.status_code == 200
    
    # Strict validation against Pydantic schema
    order = OrderResponse.model_validate(response.json())
    assert order.side == "BUY"
    assert order.status in ["PENDING", "PARTIALLY_FILLED", "FILLED"]
    assert order.bond is not None


def test_analytics_contract(live_auth_session):
    """Contract Test: GET /analytics/ returns AnalyticsSummary schema"""
    response = live_auth_session.get(f"{BASE_URL}/api/v1/analytics/")
    assert response.status_code == 200
    
    # Strict validation against Pydantic schema
    analytics = AnalyticsSummary.model_validate(response.json())
    assert isinstance(analytics.total_trades_count, int)
    assert isinstance(analytics.yield_curve, list)
