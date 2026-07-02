import asyncio
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models import Trade, User, SettlementStatus
from backend.app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

class SettlementService:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._settlement_loop())
        logger.info("Settlement Service background worker started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Settlement Service background worker stopped.")

    async def trigger_settlement_worker(self):
        """Allows other services to notify the settlement loop to wake up and process immediately."""
        # Simple yield to run immediately
        await asyncio.sleep(0.1)

    async def _settlement_loop(self):
        while self._running:
            try:
                db = SessionLocal()
                # 1. Process EXECUTED trades -> CLEARED (immediate transition)
                executed_trades = db.query(Trade).filter(
                    Trade.settlement_status == SettlementStatus.EXECUTED
                ).all()
                
                for trade in executed_trades:
                    trade.settlement_status = SettlementStatus.CLEARED
                    db.add(trade)
                    
                    # Notify buyer and seller
                    await self._notify_trade_update(trade, "cleared")
                
                db.commit()

                # 2. Process CLEARED trades -> SETTLED or FAILED (after 12-15 seconds)
                # Select trades that have been in CLEARED status for more than 12 seconds
                cutoff_time = datetime.utcnow() - timedelta(seconds=12)
                cleared_trades = db.query(Trade).filter(
                    Trade.settlement_status == SettlementStatus.CLEARED,
                    Trade.executed_at <= cutoff_time
                ).all()

                for trade in cleared_trades:
                    # 97% success rate, 3% failure rate for simulation realism
                    if random.random() < 0.97:
                        trade.settlement_status = SettlementStatus.SETTLED
                        trade.settled_at = datetime.utcnow()
                        db.add(trade)
                        db.commit()
                        logger.info(f"Trade {trade.id} settled successfully.")
                        await self._notify_trade_update(trade, "settled")
                    else:
                        # Trade failed settlement! Rollback cash balances
                        trade.settlement_status = SettlementStatus.FAILED
                        trade.settled_at = datetime.utcnow()
                        db.add(trade)
                        
                        # Revert cash balances
                        buyer = db.query(User).filter(User.id == trade.buyer_id).first()
                        seller = db.query(User).filter(User.id == trade.seller_id).first()
                        
                        # Refund cash to buyer
                        if buyer and buyer.id != 0: # 0 is simulated market
                            buyer.cash_balance += trade.principal
                            db.add(buyer)
                            
                        # Subtract cash from seller
                        if seller and seller.id != 0:
                            seller.cash_balance -= trade.principal
                            db.add(seller)
                            
                        db.commit()
                        logger.warning(f"Trade {trade.id} failed settlement. Cash balances rolled back.")
                        await self._notify_trade_update(trade, "failed", reason="Securities delivery failure (clearing fail)")
                
                db.close()
            except Exception as e:
                logger.error(f"Error in settlement loop: {e}", exc_info=True)
                
            # Tick every 3 seconds
            await asyncio.sleep(3.0)

    async def _notify_trade_update(self, trade: Trade, status_str: str, reason: str = None):
        """Helper to send WebSocket messages to the involved parties of a trade update."""
        msg = {
            "type": "trade_settlement_update",
            "data": {
                "trade_id": trade.id,
                "status": trade.settlement_status,
                "principal": trade.principal,
                "price": trade.price,
                "quantity": trade.quantity,
                "reason": reason,
                "timestamp": trade.settled_at.isoformat() if trade.settled_at else trade.executed_at.isoformat()
            }
        }
        
        # Notify buyer
        if trade.buyer_id != 0:
            await manager.send_personal_message(msg, trade.buyer_id)
            
        # Notify seller
        if trade.seller_id != 0:
            await manager.send_personal_message(msg, trade.seller_id)
            
        # Also broadcast to public ledger for blotter views
        await manager.broadcast({
            "type": "blotter_update",
            "data": {
                "trade_id": trade.id,
                "status": trade.settlement_status,
                "buyer_id": trade.buyer_id,
                "seller_id": trade.seller_id
            }
        })

# Instantiate the singleton settlement service
settlement_service = SettlementService()
