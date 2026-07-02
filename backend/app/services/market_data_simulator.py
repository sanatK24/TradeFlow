import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models import Bond, Order, OrderStatus
from backend.app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

# Standard US Treasuries and Corporate Bonds to seed
INITIAL_BONDS = [
    {
        "isin": "US912828YL46",
        "ticker": "US02Y",
        "name": "US Treasury 2-Year",
        "coupon": 4.25,
        "maturity_date": "2028-06-30",
        "type": "TREASURY",
        "last_price": 99.85
    },
    {
        "isin": "US912828ZM29",
        "ticker": "US05Y",
        "name": "US Treasury 5-Year",
        "coupon": 4.125,
        "maturity_date": "2031-06-30",
        "type": "TREASURY",
        "last_price": 99.40
    },
    {
        "isin": "US912810QL12",
        "ticker": "US10Y",
        "name": "US Treasury 10-Year",
        "coupon": 4.00,
        "maturity_date": "2036-06-30",
        "type": "TREASURY",
        "last_price": 98.50
    },
    {
        "isin": "US912810FT20",
        "ticker": "US30Y",
        "name": "US Treasury 30-Year",
        "coupon": 4.50,
        "maturity_date": "2056-06-30",
        "type": "TREASURY",
        "last_price": 97.20
    },
    {
        "isin": "US037833DL99",
        "ticker": "AAPL34",
        "name": "Apple Inc 4.30% 2034",
        "coupon": 4.30,
        "maturity_date": "2034-05-10",
        "type": "CORPORATE",
        "last_price": 100.20
    },
    {
        "isin": "US594918DL88",
        "ticker": "MSFT34",
        "name": "Microsoft Corp 4.00% 2034",
        "coupon": 4.00,
        "maturity_date": "2034-02-08",
        "type": "CORPORATE",
        "last_price": 98.90
    },
    {
        "isin": "US88160RDL33",
        "ticker": "TSLA31",
        "name": "Tesla Inc 5.50% 2031",
        "coupon": 5.50,
        "maturity_date": "2031-11-15",
        "type": "CORPORATE",
        "last_price": 101.50
    }
]

def calculate_years_to_maturity(maturity_date_str: str) -> float:
    try:
        maturity_year = int(maturity_date_str.split("-")[0])
        current_year = datetime.now().year
        return max(0.5, float(maturity_year - current_year))
    except Exception:
        return 5.0

def calculate_ytm(price: float, coupon: float, years: float, face_value: float = 100.0) -> float:
    """Approximates Yield to Maturity (YTM) for a bond."""
    if price <= 0:
        return 0.0
    # Standard YTM approximation:
    # YTM approx = [Coupon + (FaceValue - Price) / Years] / [(FaceValue + Price) / 2]
    numerator = coupon + (face_value - price) / max(0.1, years)
    denominator = (face_value + price) / 2.0
    ytm = (numerator / denominator) * 100.0
    return round(max(0.01, ytm), 3)

def calculate_bond_price(yield_pct: float, coupon: float, years: float, face_value: float = 100.0) -> float:
    """Calculates bond price from yield using the standard discount cash flow formula."""
    r = yield_pct / 100.0
    if r <= 0:
        r = 0.0001
    # Simple annual coupon discount model
    annuity_factor = (1 - (1 + r) ** (-years)) / r
    discounted_face = face_value * ((1 + r) ** (-years))
    price = coupon * annuity_factor + discounted_face
    return round(price, 3)

class MarketDataSimulator:
    def __init__(self):
        # Stores Level 2 order books for each bond_id:
        # { bond_id: { "bids": [{"price": p, "qty": q}], "asks": [...] } }
        self.order_books: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        # Stores bond tickers mapping: { ticker: bond_id }
        self.bond_tickers: Dict[str, int] = {}
        self._running = False
        self._task = None

    def seed_bonds(self, db: Session):
        """Seeds initial bonds into the DB if empty."""
        existing_count = db.query(Bond).count()
        if existing_count == 0:
            logger.info("Seeding initial bonds database...")
            for b_data in INITIAL_BONDS:
                years = calculate_years_to_maturity(b_data["maturity_date"])
                ytm = calculate_ytm(b_data["last_price"], b_data["coupon"], years)
                
                bond = Bond(
                    isin=b_data["isin"],
                    ticker=b_data["ticker"],
                    name=b_data["name"],
                    coupon=b_data["coupon"],
                    maturity_date=b_data["maturity_date"],
                    type=b_data["type"],
                    face_value=1000.0,  # standard par value
                    last_price=b_data["last_price"],
                    yield_to_maturity=ytm
                )
                db.add(bond)
            db.commit()
            logger.info("Seeding bonds completed.")
        
        # Populate ticker-to-id mapping
        bonds = db.query(Bond).all()
        for b in bonds:
            self.bond_tickers[b.ticker] = b.id
            if b.id not in self.order_books:
                self.order_books[b.id] = {"bids": [], "asks": []}

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info("Market Data Simulator started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Market Data Simulator stopped.")

    async def _simulation_loop(self):
        await asyncio.sleep(2.0)  # wait for startup
        while self._running:
            try:
                db = SessionLocal()
                bonds = db.query(Bond).all()
                
                for bond in bonds:
                    # 1. Random Walk mid price
                    # Shift price slightly by -0.05 to +0.05 clean price points
                    price_change = random.choice([-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03])
                    # Ensure treasury bonds stay close to 95-105 range for realism
                    new_price = round(bond.last_price + price_change, 2)
                    if new_price < 85.0:
                        new_price = 85.0
                    elif new_price > 115.0:
                        new_price = 115.0
                    
                    years = calculate_years_to_maturity(bond.maturity_date)
                    ytm = calculate_ytm(new_price, bond.coupon, years)
                    
                    # Update DB
                    bond.last_price = new_price
                    bond.yield_to_maturity = ytm
                    db.add(bond)
                    
                    # 2. Re-generate Level 2 Order Book bids/asks
                    # Spread is narrow (0.01 - 0.04) for Treasuries, wider (0.05 - 0.15) for Corporates
                    spread = round(random.uniform(0.01, 0.03) if bond.type == "TREASURY" else random.uniform(0.06, 0.15), 3)
                    
                    bids = []
                    asks = []
                    
                    # Generate 4 levels
                    for i in range(1, 5):
                        bid_price = round(new_price - (spread / 2.0) - (i - 1) * 0.02, 3)
                        ask_price = round(new_price + (spread / 2.0) + (i - 1) * 0.02, 3)
                        
                        # Sizes in face value (multiples of 1000, usually 1M to 10M)
                        bid_qty = random.randint(1, 10) * 1000
                        ask_qty = random.randint(1, 10) * 1000
                        
                        bids.append({"price": bid_price, "qty": bid_qty})
                        asks.append({"price": ask_price, "qty": ask_qty})
                    
                    self.order_books[bond.id] = {
                        "bids": bids,
                        "asks": asks
                    }
                    
                    # 3. Simulate hitting user pending orders
                    # If any user LIMIT BUY is at or above our ask, or LIMIT SELL at or below our bid, match it.
                    # Or with a 10% random chance, "market interest" hits the user's resting limit order if it is near the mid-price.
                    await self._match_resting_orders(db, bond.id, bids[0]["price"], asks[0]["price"])

                    # 4. Broadcast book updates via WS
                    await manager.broadcast({
                        "type": "order_book_update",
                        "data": {
                            "bond_id": bond.id,
                            "ticker": bond.ticker,
                            "name": bond.name,
                            "coupon": bond.coupon,
                            "maturity_date": bond.maturity_date,
                            "type": bond.type,
                            "last_price": new_price,
                            "yield": ytm,
                            "bids": bids,
                            "asks": asks
                        }
                    })
                
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Error in Market Simulator Loop: {e}", exc_info=True)
            
            # Tick every 2 seconds
            await asyncio.sleep(2.0)

    async def _match_resting_orders(self, db: Session, bond_id: int, top_bid: float, top_ask: float):
        """Simulates outside market forces matching the user's pending limit orders if market crosses them."""
        from backend.app.services.matching_engine import matching_engine
        
        # Get active orders
        pending_orders = db.query(Order).filter(
            Order.bond_id == bond_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
        ).all()
        
        for order in pending_orders:
            matched = False
            # If user wants to BUY, and their limit price is >= the market ask price
            if order.side == "BUY" and order.price >= top_ask:
                matched = True
                match_price = top_ask
            # If user wants to SELL, and their limit price is <= the market bid price
            elif order.side == "SELL" and order.price <= top_bid:
                matched = True
                match_price = top_bid
            # Random fill chance (5%) for resting orders close to the mid price
            elif random.random() < 0.05:
                matched = True
                match_price = order.price
            
            if matched:
                # Execute the match against simulated dealer liquidity
                # Dealer is represented by a simulated counterparty ID (we can set to 0 or another simulated broker system)
                logger.info(f"Simulated market matches user limit order {order.id} ({order.side} {order.quantity} @ {order.price}) at price {match_price}")
                
                # Execute transaction using the matching engine
                # Since matching engine is defined in another module, we trigger it.
                # To prevent circular imports, we import and execute:
                await matching_engine.execute_simulated_fill(db, order, match_price)

# Instantiate the singleton simulator
market_simulator = MarketDataSimulator()
