from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.database import get_db
from backend.app.models import Trade, User, Bond
from backend.app.schemas import TradeBlotterResponse
from backend.app.routes.auth import get_current_user

router = APIRouter(prefix="/trades", tags=["Trades / Blotter"])

@router.get("/", response_model=List[TradeBlotterResponse])
def get_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all trades where the current user was either the buyer or the seller (Trade Blotter)."""
    # Fetch trades involving current user (exclude system-only trades if any)
    trades = db.query(Trade).filter(
        or_(Trade.buyer_id == current_user.id, Trade.seller_id == current_user.id)
    ).order_by(Trade.executed_at.desc()).all()
    
    # Pre-cache user mapping for fast lookup
    user_ids = set()
    for t in trades:
        user_ids.add(t.buyer_id)
        user_ids.add(t.seller_id)
        
    users = db.query(User).filter(User.id.in_(list(user_ids))).all()
    user_map = {u.id: u.username for u in users}
    user_map[0] = "STREET_LIQUIDITY" # Simulated Dealer Desk representation
    
    blotter = []
    for t in trades:
        buyer_name = user_map.get(t.buyer_id, f"User {t.buyer_id}")
        seller_name = user_map.get(t.seller_id, f"User {t.seller_id}")
        
        # side is relative to the user requesting the blotter
        side = "BUY" if t.buyer_id == current_user.id else "SELL"
        
        blotter.append(
            TradeBlotterResponse(
                id=t.id,
                bond_ticker=t.bond.ticker,
                bond_name=t.bond.name,
                buyer_name=buyer_name,
                seller_name=seller_name,
                side=side,
                price=t.price,
                quantity=t.quantity,
                principal=t.principal,
                settlement_status=t.settlement_status,
                executed_at=t.executed_at,
                settled_at=t.settled_at
            )
        )
        
    return blotter
