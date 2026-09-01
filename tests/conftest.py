"""
Root conftest.py — Shared fixtures for all TradeFlow test tiers.

Provides:
- test_db: Isolated SQLite database session with seeded bonds & system user
- test_app: FastAPI TestClient with dependency overrides
- auth_headers: Pre-authenticated Bearer token headers

IMPORTANT: This module must set DATABASE_URL *before* any backend imports
so the SQLAlchemy engine uses SQLite instead of the production Supabase DB.
"""

import os

# ── Override env vars BEFORE any backend imports ──
os.environ["DATABASE_URL"] = "sqlite:///./test_tradeflow.db"
os.environ["REDIS_URL"] = ""  # force mock Redis

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.models import User, Bond
from backend.app.routes.auth import get_password_hash


# ---------------------------------------------------------------------------
# In-memory SQLite engine for API tests
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///./test_tradeflow.db"

test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# Seed data matching the production MarketDataSimulator.INITIAL_BONDS
SEED_BONDS = [
    {
        "isin": "US912828YL46", "ticker": "US02Y",
        "name": "US Treasury 2-Year", "coupon": 4.25,
        "maturity_date": "2028-06-30", "type": "TREASURY",
        "face_value": 1000.0, "last_price": 99.85, "yield_to_maturity": 4.3,
    },
    {
        "isin": "US912828ZM29", "ticker": "US05Y",
        "name": "US Treasury 5-Year", "coupon": 4.125,
        "maturity_date": "2031-06-30", "type": "TREASURY",
        "face_value": 1000.0, "last_price": 99.40, "yield_to_maturity": 4.2,
    },
    {
        "isin": "US912810QL12", "ticker": "US10Y",
        "name": "US Treasury 10-Year", "coupon": 4.00,
        "maturity_date": "2036-06-30", "type": "TREASURY",
        "face_value": 1000.0, "last_price": 98.50, "yield_to_maturity": 4.15,
    },
    {
        "isin": "US912810FT20", "ticker": "US30Y",
        "name": "US Treasury 30-Year", "coupon": 4.50,
        "maturity_date": "2056-06-30", "type": "TREASURY",
        "face_value": 1000.0, "last_price": 97.20, "yield_to_maturity": 4.65,
    },
    {
        "isin": "US037833DL99", "ticker": "AAPL34",
        "name": "Apple Inc 4.30% 2034", "coupon": 4.30,
        "maturity_date": "2034-05-10", "type": "CORPORATE",
        "face_value": 1000.0, "last_price": 100.20, "yield_to_maturity": 4.27,
    },
    {
        "isin": "US594918DL88", "ticker": "MSFT34",
        "name": "Microsoft Corp 4.00% 2034", "coupon": 4.00,
        "maturity_date": "2034-02-08", "type": "CORPORATE",
        "face_value": 1000.0, "last_price": 98.90, "yield_to_maturity": 4.15,
    },
    {
        "isin": "US88160RDL33", "ticker": "TSLA31",
        "name": "Tesla Inc 5.50% 2031", "coupon": 5.50,
        "maturity_date": "2031-11-15", "type": "CORPORATE",
        "face_value": 1000.0, "last_price": 101.50, "yield_to_maturity": 5.2,
    },
]


def _seed_database(db):
    """Populate the test DB with system user and bond instruments."""
    # System market-maker bot (id=0)
    system_user = User(
        id=0,
        username="STREET_LIQUIDITY",
        password_hash=get_password_hash("streetliquiditypass123"),
        cash_balance=1_000_000_000_000.0,
    )
    db.add(system_user)

    for b in SEED_BONDS:
        db.add(Bond(**b))

    db.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db():
    """Yields a clean database session. Tables are created before and dropped after each test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    _seed_database(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def _get_test_db_override(db_session):
    """Returns a dependency override generator that yields the given session."""
    def override():
        try:
            yield db_session
        finally:
            pass  # session is closed by the test_db fixture
    return override


@pytest.fixture(scope="function")
def test_app(test_db):
    """
    Provides a FastAPI TestClient with the DB dependency overridden
    to use the test database. Background simulators are NOT started.
    """
    # We must re-bind the app's database engine to our test engine so that
    # the `from backend.app.database import engine` used in startup events
    # also points to the test SQLite DB (already handled via env var override).
    from backend.app.main import app

    app.dependency_overrides[get_db] = _get_test_db_override(test_db)

    # Seed the order books in redis mock so bonds/order-book endpoint works
    from backend.app.services.redis_service import redis_service
    bonds = test_db.query(Bond).all()
    for b in bonds:
        redis_service.set_cache(f"order_book:{b.id}", {
            "bids": [{"price": round(b.last_price - 0.05, 3), "qty": 5000}],
            "asks": [{"price": round(b.last_price + 0.05, 3), "qty": 5000}],
        })

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(test_app):
    """
    Registers a test user and returns Authorization headers with a valid JWT token.
    """
    # Register
    test_app.post(
        "/api/v1/auth/register",
        json={"username": "testtrader", "password": "TestPass123!"},
    )
    # Login to get token (uses OAuth2PasswordRequestForm — form data, not JSON)
    resp = test_app.post(
        "/api/v1/auth/token",
        data={"username": "testtrader", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
