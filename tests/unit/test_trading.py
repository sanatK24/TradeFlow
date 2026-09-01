"""
Ported unit tests for the TradeFlow matching engine and bond math.

Originally from backend/app/tests/test_trading.py (unittest.TestCase),
converted to pytest-style functions with fixtures.
"""

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models import User, Bond, Order, Trade, OrderStatus, SettlementStatus
from backend.app.services.market_data_simulator import calculate_ytm, calculate_bond_price
from backend.app.services.matching_engine import MatchingEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unit_db():
    """Creates a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()

    # Seed system bot and test trader
    market_bot = User(
        id=0,
        username="STREET_LIQUIDITY",
        password_hash="hash",
        cash_balance=1_000_000_000.0,
    )
    trader = User(
        id=1,
        username="TestTrader",
        password_hash="hash",
        cash_balance=100_000.0,  # $100k test capital
    )
    bond = Bond(
        id=10,
        isin="US10YTEST01",
        ticker="US10Y",
        name="US Treasury 10-Year Test",
        coupon=4.00,
        maturity_date="2036-06-30",
        type="TREASURY",
        face_value=1000.0,
        last_price=100.00,
        yield_to_maturity=4.00,
    )
    db.add_all([market_bot, trader, bond])
    db.commit()

    yield db, trader, bond

    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def matching_engine():
    return MatchingEngine()


# ---------------------------------------------------------------------------
# Bond Math Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBondMath:
    """Tests for YTM and price calculation helper functions."""

    def test_ytm_at_par(self):
        """Coupon: 4.0%, Price: 100.0, Years: 10 => Yield ≈ 4.0%."""
        ytm = calculate_ytm(price=100.0, coupon=4.0, years=10.0)
        assert round(ytm, 1) == pytest.approx(4.0, abs=0.2)

    def test_ytm_discount_price(self):
        """Price below par => Yield should exceed coupon rate."""
        ytm = calculate_ytm(price=95.0, coupon=4.0, years=10.0)
        assert ytm > 4.0

    def test_ytm_premium_price(self):
        """Price above par => Yield should be below coupon rate."""
        ytm = calculate_ytm(price=105.0, coupon=4.0, years=10.0)
        assert ytm < 4.0

    def test_bond_price_from_yield_at_par(self):
        """Yield = coupon => Price ≈ par (100)."""
        price = calculate_bond_price(yield_pct=4.0, coupon=4.0, years=10.0)
        assert price == pytest.approx(100.0, abs=0.5)

    def test_bond_price_inverse_relationship(self):
        """Higher yield => lower price."""
        price_low_yield = calculate_bond_price(yield_pct=3.0, coupon=4.0, years=10.0)
        price_high_yield = calculate_bond_price(yield_pct=5.0, coupon=4.0, years=10.0)
        assert price_low_yield > price_high_yield


# ---------------------------------------------------------------------------
# Matching Engine Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMatchingEngine:
    """Tests for the order matching engine business logic."""

    def test_insufficient_funds_cancels_order(self, unit_db, matching_engine):
        """
        Trader has $100k. Places BUY 200 bonds @ 105.0.
        Principal = 200 * 105 * (1000/100) = $210,000 > $100k => CANCELLED.
        """
        db, trader, bond = unit_db

        order = Order(
            id=101,
            user_id=trader.id,
            bond_id=bond.id,
            side="BUY",
            type="LIMIT",
            price=105.0,
            quantity=200,
            remaining_qty=200,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()

        loop = asyncio.new_event_loop()
        processed = loop.run_until_complete(matching_engine.process_order(db, order))
        loop.close()

        assert processed.status == OrderStatus.CANCELLED
        assert trader.cash_balance == 100_000.0  # Untouched

    def test_short_selling_limit_cancels_order(self, unit_db, matching_engine):
        """
        Trader tries to SELL 60,000 bonds (exceeding -50,000 short limit) => CANCELLED.
        """
        db, trader, bond = unit_db

        order = Order(
            id=102,
            user_id=trader.id,
            bond_id=bond.id,
            side="SELL",
            type="LIMIT",
            price=99.0,
            quantity=60000,
            remaining_qty=60000,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()

        loop = asyncio.new_event_loop()
        processed = loop.run_until_complete(matching_engine.process_order(db, order))
        loop.close()

        assert processed.status == OrderStatus.CANCELLED
