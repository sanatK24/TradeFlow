from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    cash_balance: float
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int
    cash_balance: float

class TokenData(BaseModel):
    username: Optional[str] = None


# --- Bond Schemas ---
class BondBase(BaseModel):
    isin: str
    ticker: str
    name: str
    coupon: float
    maturity_date: str
    type: str
    face_value: float

class BondResponse(BondBase):
    id: int
    last_price: float
    yield_to_maturity: float

    class Config:
        from_attributes = True


# --- Order Schemas ---
class OrderCreate(BaseModel):
    bond_id: int
    side: str  # BUY or SELL
    type: str  # LIMIT or MARKET
    price: float  # Clean price % (e.g. 99.5)
    quantity: int

class OrderResponse(BaseModel):
    id: int
    user_id: int
    bond_id: int
    side: str
    type: str
    price: float
    quantity: int
    remaining_qty: int
    status: str
    created_at: datetime
    bond: BondResponse

    class Config:
        from_attributes = True


# --- Quote Schemas ---
class QuoteCreate(BaseModel):
    price: float

class QuoteResponse(BaseModel):
    id: int
    rfq_id: int
    dealer_name: str
    price: float
    yield_pct: float
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# --- RFQ Schemas ---
class RfqCreate(BaseModel):
    bond_id: int
    side: str  # BUY or SELL (relative to the client)
    quantity: int

class RfqResponse(BaseModel):
    id: int
    client_id: int
    bond_id: int
    side: str
    quantity: int
    status: str
    expires_at: datetime
    created_at: datetime
    bond: BondResponse
    quotes: List[QuoteResponse] = []

    class Config:
        from_attributes = True


# --- Trade Schemas ---
class TradeResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    rfq_id: Optional[int] = None
    buyer_id: int
    seller_id: int
    bond_id: int
    price: float
    quantity: int
    principal: float
    settlement_status: str
    executed_at: datetime
    settled_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TradeBlotterResponse(BaseModel):
    id: int
    bond_ticker: str
    bond_name: str
    buyer_name: str
    seller_name: str
    side: str  # BUY or SELL relative to the current user
    price: float
    quantity: int
    principal: float
    settlement_status: str
    executed_at: datetime
    settled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Analytics Schemas ---
class YieldCurvePoint(BaseModel):
    ticker: str
    maturity_years: float
    yield_pct: float

class AnalyticsSummary(BaseModel):
    total_trades_count: int
    total_volume_millions: float
    user_pnl: float
    user_cash: float
    rfq_win_rate: float
    rfq_avg_response_time: float
    yield_curve: List[YieldCurvePoint]
    bond_distribution: List[dict]  # e.g., [{"name": "US10Y", "value": 15000000}]
    monthly_volumes: List[dict]    # e.g., [{"time": "10:00", "volume": 5.2}]
