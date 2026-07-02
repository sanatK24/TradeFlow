import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models import User, Bond, Order, Trade, OrderStatus, SettlementStatus
from backend.app.services.market_data_simulator import calculate_ytm, calculate_bond_price
from backend.app.services.matching_engine import MatchingEngine

class TestTradingSimulator(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.matching_engine = MatchingEngine()

        # Seed test user and bond
        # User ID 0 is simulated market
        self.market_bot = User(id=0, username="STREET_LIQUIDITY", password_hash="hash", cash_balance=1000000000.0)
        self.trader = User(id=1, username="TestTrader", password_hash="hash", cash_balance=100000.0) # $100k test capital
        
        self.bond = Bond(
            id=10,
            isin="US10YTEST01",
            ticker="US10Y",
            name="US Treasury 10-Year Test",
            coupon=4.00,
            maturity_date="2036-06-30",
            type="TREASURY",
            face_value=1000.0,
            last_price=100.00,
            yield_to_maturity=4.00
        )
        
        self.db.add(self.market_bot)
        self.db.add(self.trader)
        self.db.add(self.bond)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_bond_math(self):
        # 1. Test YTM calculation approximation
        # Coupon: 4.0%, Price: 100.0, Years: 10 => Yield should be approx 4.0%
        ytm = calculate_ytm(price=100.0, coupon=4.0, years=10.0)
        self.assertAlmostEqual(ytm, 4.0, places=1)

        # Price down (discount) => Yield should go up
        ytm_disc = calculate_ytm(price=95.0, coupon=4.0, years=10.0)
        self.assertTrue(ytm_disc > 4.0)

        # Price up (premium) => Yield should go down
        ytm_prem = calculate_ytm(price=105.0, coupon=4.0, years=10.0)
        self.assertTrue(ytm_prem < 4.0)

        # 2. Test bond price discount calculation from yield
        price = calculate_bond_price(yield_pct=4.0, coupon=4.0, years=10.0)
        # Yield = coupon => Price = par (100)
        self.assertAlmostEqual(price, 100.0, places=1)

    def test_insufficient_funds_cancel(self):
        # Trader has $100k cash.
        # Places order to BUY 200 bonds @ 105.0
        # Face value = 1000, so principal = 200 * 105 * (1000 / 100) = $210,000.
        # This exceeds their $100k balance, so order should cancel.
        order = Order(
            id=101,
            user_id=self.trader.id,
            bond_id=self.bond.id,
            side="BUY",
            type="LIMIT",
            price=105.0,
            quantity=200,
            remaining_qty=200,
            status=OrderStatus.PENDING
        )
        self.db.add(order)
        self.db.commit()

        # Run process_order (which will evaluate and cancel due to balance checks)
        import asyncio
        async def run_test():
            return await self.matching_engine.process_order(self.db, order)
        
        loop = asyncio.new_event_loop()
        processed_order = loop.run_until_complete(run_test())
        loop.close()

        self.assertEqual(processed_order.status, OrderStatus.CANCELLED)
        # Cash should remain untouched
        self.assertEqual(self.trader.cash_balance, 100000.0)

    def test_short_selling_limits(self):
        # Trader tries to SELL 60,000 bonds (exceeding short selling limit of -50,000)
        order = Order(
            id=102,
            user_id=self.trader.id,
            bond_id=self.bond.id,
            side="SELL",
            type="LIMIT",
            price=99.0,
            quantity=60000,
            remaining_qty=60000,
            status=OrderStatus.PENDING
        )
        self.db.add(order)
        self.db.commit()

        import asyncio
        async def run_test():
            return await self.matching_engine.process_order(self.db, order)
        
        loop = asyncio.new_event_loop()
        processed_order = loop.run_until_complete(run_test())
        loop.close()

        self.assertEqual(processed_order.status, OrderStatus.CANCELLED)

if __name__ == "__main__":
    unittest.main()
