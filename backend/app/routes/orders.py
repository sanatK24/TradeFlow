from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Order, OrderStatus, Bond, User
from backend.app.schemas import OrderCreate, OrderResponse
from backend.app.services.matching_engine import matching_engine
from backend.app.routes.auth import get_current_user
from backend.app.websocket.connection_manager import manager

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submits a BUY or SELL order. Triggers matching engine execution."""
    bond = db.query(Bond).filter(Bond.id == order_in.bond_id).first()
    if not bond:
        raise HTTPException(status_code=404, detail="Bond not found")

    # Create new order record
    db_order = Order(
        user_id=current_user.id,
        bond_id=order_in.bond_id,
        side=order_in.side.upper(),
        type=order_in.type.upper(),
        price=order_in.price,
        quantity=order_in.quantity,
        remaining_qty=order_in.quantity,
        status=OrderStatus.PENDING
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Process order immediately through matching engine
    processed_order = await matching_engine.process_order(db, db_order)
    db.refresh(processed_order)
    return processed_order

@router.get("/", response_model=List[OrderResponse])
def get_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves order history for the current authenticated user."""
    query = db.query(Order).filter(Order.user_id == current_user.id)
    if status:
        query = query.filter(Order.status == status.upper())
    orders = query.order_by(Order.created_at.desc()).all()
    return orders

@router.get("/open", response_model=List[OrderResponse])
def get_open_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all currently active/open orders for the user."""
    orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
    ).order_by(Order.created_at.desc()).all()
    return orders

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels a pending order if it hasn't been completely filled yet."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be cancelled because it is already {order.status}"
        )

    # Update order state
    order.status = OrderStatus.CANCELLED
    db.add(order)
    db.commit()
    db.refresh(order)

    # Notify client WebSocket
    await manager.send_personal_message({
        "type": "order_cancelled",
        "data": {
            "order_id": order.id,
            "ticker": order.bond.ticker,
            "status": order.status
        }
    }, current_user.id)

    return order
