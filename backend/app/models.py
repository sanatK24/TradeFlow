from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.app.database import Base

class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, enum.Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"

class RfqStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class SettlementStatus(str, enum.Enum):
    EXECUTED = "EXECUTED"
    CLEARED = "CLEARED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    cash_balance = Column(Float, default=100000000.0)  # $100M default trading account capital
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="user")
    rfqs = relationship("RFQ", back_populates="client")
    # Trades where the user is buyer or seller
    bought_trades = relationship("Trade", foreign_keys="[Trade.buyer_id]", back_populates="buyer")
    sold_trades = relationship("Trade", foreign_keys="[Trade.seller_id]", back_populates="seller")

class Bond(Base):
    __tablename__ = "bonds"

    id = Column(Integer, primary_key=True, index=True)
    isin = Column(String, unique=True, index=True, nullable=False)  # International Securities Identification Number
    ticker = Column(String, unique=True, index=True, nullable=False)  # US10Y, AAPL34, etc.
    name = Column(String, nullable=False)
    coupon = Column(Float, nullable=False)  # Coupon rate e.g., 4.25 (represented in %)
    maturity_date = Column(String, nullable=False)  # E.g., "2034-06-15"
    type = Column(String, nullable=False)  # "TREASURY" or "CORPORATE"
    face_value = Column(Float, default=1000.0)  # Face value of a single bond (usually $1000)
    last_price = Column(Float, default=100.0)  # Clean price (as % of face value, e.g. 100.0 or 99.50)
    yield_to_maturity = Column(Float, default=4.0)  # Annualized yield in %

    # Relationships
    orders = relationship("Order", back_populates="bond")
    rfqs = relationship("RFQ", back_populates="bond")
    trades = relationship("Trade", back_populates="bond")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bond_id = Column(Integer, ForeignKey("bonds.id"), nullable=False)
    side = Column(String, nullable=False)  # BUY or SELL
    type = Column(String, nullable=False)  # LIMIT or MARKET
    price = Column(Float, nullable=False)  # Clean price as % of face value
    quantity = Column(Integer, nullable=False)  # Number of bonds (contracts)
    remaining_qty = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, FILLED, PARTIALLY_FILLED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    bond = relationship("Bond", back_populates="orders")
    trades = relationship("Trade", back_populates="order")

class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bond_id = Column(Integer, ForeignKey("bonds.id"), nullable=False)
    side = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)  # Number of bonds
    status = Column(String, default="REQUESTED")  # REQUESTED, QUOTED, ACCEPTED, REJECTED, EXPIRED
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("User", back_populates="rfqs")
    bond = relationship("Bond", back_populates="rfqs")
    quotes = relationship("Quote", back_populates="rfq", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="rfq")

class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=False)
    dealer_name = Column(String, nullable=False)  # JPMorgan, Goldman Sachs, or "User" (if user acts as dealer)
    price = Column(Float, nullable=False)  # clean price percentage
    yield_pct = Column(Float, nullable=False)  # computed yield in %
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rfq = relationship("RFQ", back_populates="quotes")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Null if executed via RFQ
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=True)  # Null if executed via order book
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bond_id = Column(Integer, ForeignKey("bonds.id"), nullable=False)
    price = Column(Float, nullable=False)  # Clean price percentage
    quantity = Column(Integer, nullable=False)  # Quantity of bonds
    principal = Column(Float, nullable=False)  # Dollar amount of trade (qty * price * face_value / 100)
    settlement_status = Column(String, default="EXECUTED")  # EXECUTED, CLEARED, SETTLED, FAILED
    executed_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="trades")
    rfq = relationship("RFQ", back_populates="trades")
    bond = relationship("Bond", back_populates="trades")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="bought_trades")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="sold_trades")
