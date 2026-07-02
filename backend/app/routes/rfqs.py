from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import RFQ, Quote, Bond, User, RfqStatus, Trade, SettlementStatus
from backend.app.schemas import RfqCreate, RfqResponse, QuoteCreate
from backend.app.services.rfq_manager import rfq_manager
from backend.app.services.settlement_service import settlement_service
from backend.app.routes.auth import get_current_user
from backend.app.websocket.connection_manager import manager

router = APIRouter(prefix="/rfqs", tags=["Request For Quote (RFQ)"])

@router.post("/", response_model=RfqResponse)
async def create_client_rfq(
    rfq_in: RfqCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Client Mode: Submits an RFQ to buy/sell bonds. Spawns dealer quote generator in 1-3 seconds."""
    bond = db.query(Bond).filter(Bond.id == rfq_in.bond_id).first()
    if not bond:
        raise HTTPException(status_code=404, detail="Bond not found")

    # Expiry is 30 seconds for client RFQs
    expires_at = datetime.utcnow() + timedelta(seconds=30)
    
    rfq = RFQ(
        client_id=current_user.id,
        bond_id=rfq_in.bond_id,
        side=rfq_in.side.upper(),
        quantity=rfq_in.quantity,
        status=RfqStatus.REQUESTED,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(rfq)
    db.commit()
    db.refresh(rfq)

    # Spawn background task to simulate dealer response
    asyncio.create_task(rfq_manager.generate_dealer_quotes_for_client_rfq(rfq.id))

    return rfq

@router.get("/", response_model=List[RfqResponse])
def get_client_rfqs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Client Mode: Fetch all RFQs requested by the current user."""
    rfqs = db.query(RFQ).filter(
        RFQ.client_id == current_user.id
    ).order_by(RFQ.created_at.desc()).all()
    return rfqs

@router.get("/incoming", response_model=List[RfqResponse])
def get_incoming_rfqs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dealer Mode: Fetch all active incoming client RFQs (excluding self) that can be priced."""
    now = datetime.utcnow()
    rfqs = db.query(RFQ).filter(
        RFQ.client_id == 0, # bot client
        RFQ.status == RfqStatus.REQUESTED,
        RFQ.expires_at > now
    ).order_by(RFQ.created_at.desc()).all()
    return rfqs

@router.get("/{rfq_id}", response_model=RfqResponse)
def get_rfq_details(
    rfq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detail page for a single RFQ, including quotes."""
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
        
    # Check authorization (either system bot RFQ, or requested by current user)
    if rfq.client_id != 0 and rfq.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this RFQ")
        
    return rfq

@router.post("/{rfq_id}/accept")
async def accept_dealer_quote(
    rfq_id: int,
    quote_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Client Mode: Accepts a specific dealer quote. Executes the trade and starts settlement."""
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id, RFQ.client_id == current_user.id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    if rfq.status != RfqStatus.QUOTED:
        raise HTTPException(status_code=400, detail=f"RFQ cannot be accepted in status {rfq.status}")

    if datetime.utcnow() > rfq.expires_at:
        rfq.status = RfqStatus.EXPIRED
        db.add(rfq)
        db.commit()
        raise HTTPException(status_code=400, detail="RFQ has expired")

    quote = db.query(Quote).filter(Quote.id == quote_id, Quote.rfq_id == rfq_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    bond = db.query(Bond).filter(Bond.id == rfq.bond_id).first()
    principal = rfq.quantity * quote.price * (bond.face_value / 100.0)

    # Validate buyer cash balance
    if rfq.side == "BUY":
        if current_user.cash_balance < principal:
            raise HTTPException(status_code=400, detail="Insufficient cash balance to accept this quote")
        current_user.cash_balance -= principal
        db.add(current_user)
    else:
        # Check selling limits (short sale max short position -50,000 bonds)
        from backend.app.services.matching_engine import matching_engine
        net_holding = matching_engine.get_user_holdings(db, current_user.id, bond.id)
        if net_holding - rfq.quantity < -50000:
            raise HTTPException(status_code=400, detail="Short selling limit exceeded (-50,000 bonds max)")
        current_user.cash_balance += principal
        db.add(current_user)

    # Update RFQ status
    rfq.status = RfqStatus.ACCEPTED
    db.add(rfq)

    # Create Trade record
    # User is buyer (rfq side BUY) or seller (rfq side SELL). Counterparty is simulated dealer.
    buyer_id = current_user.id if rfq.side == "BUY" else 0
    seller_id = 0 if rfq.side == "BUY" else current_user.id

    trade = Trade(
        rfq_id=rfq.id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        bond_id=bond.id,
        price=quote.price,
        quantity=rfq.quantity,
        principal=principal,
        settlement_status=SettlementStatus.EXECUTED,
        executed_at=datetime.utcnow()
    )
    db.add(trade)
    db.commit()

    # Trigger Settlement background loop
    await settlement_service.trigger_settlement_worker()

    # Notify Client WebSocket
    await manager.send_personal_message({
        "type": "rfq_accepted_confirm",
        "data": {
            "rfq_id": rfq.id,
            "ticker": bond.ticker,
            "price": quote.price,
            "qty": rfq.quantity,
            "principal": principal,
            "dealer_name": quote.dealer_name
        }
    }, current_user.id)

    return {"status": "success", "message": "Quote accepted and trade executed", "trade_id": trade.id}

@router.post("/{rfq_id}/quote")
async def submit_dealer_quote(
    rfq_id: int,
    quote_in: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dealer Mode: User submits a quote (bid/ask price) to an incoming client RFQ."""
    result = await rfq_manager.submit_user_quote(db, rfq_id, current_user.id, quote_in.price)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
