from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Bond
from backend.app.schemas import BondResponse
from backend.app.services.market_data_simulator import market_simulator
from backend.app.routes.auth import get_current_user

router = APIRouter(prefix="/bonds", tags=["Bonds"])

@router.get("/", response_model=List[BondResponse])
def get_bonds(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Fetch all tradable bonds in the system."""
    bonds = db.query(Bond).all()
    return bonds

@router.get("/{bond_id}", response_model=BondResponse)
def get_bond(bond_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get detailed information for a single bond."""
    bond = db.query(Bond).filter(Bond.id == bond_id).first()
    if not bond:
        raise HTTPException(status_code=404, detail="Bond not found")
    return bond

@router.get("/{bond_id}/order-book")
def get_bond_order_book(bond_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Fetch the current Level 2 bids and asks for a bond."""
    bond = db.query(Bond).filter(Bond.id == bond_id).first()
    if not bond:
        raise HTTPException(status_code=404, detail="Bond not found")
        
    book = market_simulator.order_books.get(bond_id, {"bids": [], "asks": []})
    return {
        "bond_id": bond.id,
        "ticker": bond.ticker,
        "last_price": bond.last_price,
        "yield": bond.yield_to_maturity,
        "bids": book["bids"],
        "asks": book["asks"]
    }
