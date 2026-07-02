import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import Order, OrderSide, OrderType, OrderStatus, Trade, User, Bond, SettlementStatus
from backend.app.websocket.connection_manager import manager
from backend.app.services.settlement_service import settlement_service

logger = logging.getLogger(__name__)

class MatchingEngine:
    def __init__(self):
        pass

    async def process_order(self, db: Session, order: Order) -> Order:
        """Processes a newly submitted order. Matches against simulated order book liquidity immediately."""
        from backend.app.services.market_data_simulator import market_simulator
        
        bond = db.query(Bond).filter(Bond.id == order.bond_id).first()
        user = db.query(User).filter(User.id == order.user_id).first()
        
        if not bond or not user:
            order.status = OrderStatus.CANCELLED
            db.commit()
            return order

        # Fetch simulated order book for matching
        book = market_simulator.order_books.get(bond.id, {"bids": [], "asks": []})
        
        # 1. Validation checks
        # Calculate cash required for BUY orders
        if order.side == "BUY":
            # Max cash needed: qty * price * (face_value / 100)
            # Normalizing bond prices: quoted as % of par. e.g. price 99.5 on face value 1000
            max_principal = order.quantity * order.price * (bond.face_value / 100.0)
            if user.cash_balance < max_principal:
                logger.warning(f"User {user.id} has insufficient balance: {user.cash_balance} < {max_principal}")
                order.status = OrderStatus.CANCELLED
                db.add(order)
                db.commit()
                # Broadcast cancel
                await manager.send_personal_message({
                    "type": "order_cancelled",
                    "data": {
                        "order_id": order.id,
                        "reason": "Insufficient cash balance"
                    }
                }, user.id)
                return order

        elif order.side == "SELL":
            # Optional: check if they have the bonds.
            # In professional trading, short selling bonds is very common. 
            # We will allow short positions but restrict it if they exceed -50,000 bonds limit.
            net_holding = self.get_user_holdings(db, user.id, bond.id)
            if net_holding - order.quantity < -50000:
                logger.warning(f"User {user.id} short limit exceeded for {bond.ticker}")
                order.status = OrderStatus.CANCELLED
                db.add(order)
                db.commit()
                await manager.send_personal_message({
                    "type": "order_cancelled",
                    "data": {
                        "order_id": order.id,
                        "reason": "Short selling limit exceeded (-50,000 bonds max short position)"
                    }
                }, user.id)
                return order

        # 2. Matching logic
        if order.type == "MARKET":
            # Execute immediately against the best available simulator levels
            liquidity_levels = book["asks"] if order.side == "BUY" else book["bids"]
            
            if not liquidity_levels:
                # No simulated liquidity, cancel order
                order.status = OrderStatus.CANCELLED
                db.add(order)
                db.commit()
                return order

            await self._fill_market_order(db, order, liquidity_levels, bond, user)

        elif order.type == "LIMIT":
            # Check if limit crosses the top of the simulated book
            top_bid = book["bids"][0]["price"] if book["bids"] else 0.0
            top_ask = book["asks"][0]["price"] if book["asks"] else 999.0
            
            if order.side == "BUY" and order.price >= top_ask:
                # Limit BUY is crossing the market ask, execute immediately
                await self._fill_limit_crossing(db, order, book["asks"], bond, user)
            elif order.side == "SELL" and order.price <= top_bid:
                # Limit SELL is crossing the market bid, execute immediately
                await self._fill_limit_crossing(db, order, book["bids"], bond, user)
            else:
                # Doesn't cross. Order sits in the book as PENDING.
                order.status = OrderStatus.PENDING
                db.add(order)
                db.commit()
                
                # Broadcast order placement update
                await manager.send_personal_message({
                    "type": "order_pending",
                    "data": {
                        "order_id": order.id,
                        "ticker": bond.ticker,
                        "side": order.side,
                        "price": order.price,
                        "qty": order.quantity,
                        "remaining_qty": order.remaining_qty,
                        "status": order.status
                    }
                }, user.id)

        return order

    def get_user_holdings(self, db: Session, user_id: int, bond_id: int) -> int:
        """Computes current net settled bond inventory of a user."""
        # Sum of bought settled bonds
        bought = db.query(func.sum(Trade.quantity)).filter(
            Trade.buyer_id == user_id,
            Trade.bond_id == bond_id,
            Trade.settlement_status == SettlementStatus.SETTLED
        ).scalar() or 0
        
        # Sum of sold settled bonds
        sold = db.query(func.sum(Trade.quantity)).filter(
            Trade.seller_id == user_id,
            Trade.bond_id == bond_id,
            Trade.settlement_status == SettlementStatus.SETTLED
        ).scalar() or 0
        
        return int(bought - sold)

    async def _fill_market_order(self, db: Session, order: Order, levels: list, bond: Bond, user: User):
        """Walks the order book levels to fill a market order."""
        remaining = order.quantity
        filled_qty = 0
        total_principal = 0.0
        
        for lvl in levels:
            if remaining <= 0:
                break
            
            lvl_price = lvl["price"]
            lvl_qty = lvl["qty"]
            
            fill_qty = min(remaining, lvl_qty)
            principal = fill_qty * lvl_price * (bond.face_value / 100.0)
            
            # For market BUY, check if user still has cash for this chunk
            if order.side == "BUY" and user.cash_balance < principal:
                # Fill as much as possible, cancel the rest
                if fill_qty > 0:
                    # Let's adjust fill_qty based on remaining cash
                    max_fill_possible = int(user.cash_balance / (lvl_price * (bond.face_value / 100.0)))
                    if max_fill_possible <= 0:
                        break
                    fill_qty = max_fill_possible
                    principal = fill_qty * lvl_price * (bond.face_value / 100.0)
                else:
                    break

            # Execute trade chunk
            trade = self._create_trade_record(db, order.id, None, order.side, fill_qty, lvl_price, principal, bond, user.id)
            
            # Adjust cash balances
            self._update_cash_balances(db, order.side, user, principal)
            
            # Update accumulators
            remaining -= fill_qty
            filled_qty += fill_qty
            total_principal += principal

        order.remaining_qty = remaining
        order.status = OrderStatus.FILLED if remaining == 0 else (OrderStatus.PARTIALLY_FILLED if filled_qty > 0 else OrderStatus.CANCELLED)
        
        db.add(order)
        db.commit()
        
        # Trigger async clearing/settlement check
        if filled_qty > 0:
            await settlement_service.trigger_settlement_worker()

        # Notify client
        await manager.send_personal_message({
            "type": "order_filled",
            "data": {
                "order_id": order.id,
                "ticker": bond.ticker,
                "side": order.side,
                "qty": order.quantity,
                "filled_qty": filled_qty,
                "remaining_qty": remaining,
                "status": order.status,
                "avg_price": round(total_principal / (filled_qty * (bond.face_value / 100.0)), 3) if filled_qty > 0 else 0
            }
        }, user.id)

    async def _fill_limit_crossing(self, db: Session, order: Order, levels: list, bond: Bond, user: User):
        """Fills a limit order that crosses the spread against simulated levels."""
        remaining = order.quantity
        filled_qty = 0
        total_principal = 0.0

        for lvl in levels:
            if remaining <= 0:
                break
            
            lvl_price = lvl["price"]
            lvl_qty = lvl["qty"]
            
            # Check if limit price still crosses
            if (order.side == "BUY" and order.price < lvl_price) or (order.side == "SELL" and order.price > lvl_price):
                break # Limit price is worse than market level, stop crossing
                
            fill_qty = min(remaining, lvl_qty)
            principal = fill_qty * lvl_price * (bond.face_value / 100.0)

            # Cash validation check for BUY
            if order.side == "BUY" and user.cash_balance < principal:
                if fill_qty > 0:
                    max_fill = int(user.cash_balance / (lvl_price * (bond.face_value / 100.0)))
                    if max_fill <= 0:
                        break
                    fill_qty = max_fill
                    principal = fill_qty * lvl_price * (bond.face_value / 100.0)
                else:
                    break

            # Create trade
            trade = self._create_trade_record(db, order.id, None, order.side, fill_qty, lvl_price, principal, bond, user.id)
            
            # Adjust balances
            self._update_cash_balances(db, order.side, user, principal)
            
            remaining -= fill_qty
            filled_qty += fill_qty
            total_principal += principal

        order.remaining_qty = remaining
        if remaining == 0:
            order.status = OrderStatus.FILLED
        elif filled_qty > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
        else:
            order.status = OrderStatus.PENDING # Becomes standard pending order
            
        db.add(order)
        db.commit()

        if filled_qty > 0:
            await settlement_service.trigger_settlement_worker()

        # Notify Client
        await manager.send_personal_message({
            "type": "order_filled" if order.status == OrderStatus.FILLED else "order_partially_filled",
            "data": {
                "order_id": order.id,
                "ticker": bond.ticker,
                "side": order.side,
                "qty": order.quantity,
                "filled_qty": filled_qty,
                "remaining_qty": remaining,
                "status": order.status,
                "avg_price": round(total_principal / (filled_qty * (bond.face_value / 100.0)), 3) if filled_qty > 0 else 0
            }
        }, user.id)

    async def execute_simulated_fill(self, db: Session, order: Order, fill_price: float):
        """Called by market simulator background thread when a user limit order gets filled by simulated ticks."""
        bond = db.query(Bond).filter(Bond.id == order.bond_id).first()
        user = db.query(User).filter(User.id == order.user_id).first()
        
        if not bond or not user:
            return

        fill_qty = order.remaining_qty
        principal = fill_qty * fill_price * (bond.face_value / 100.0)

        # Confirm cash balance for BUY fills
        if order.side == "BUY" and user.cash_balance < principal:
            # Insufficient cash to complete the fill, cancel the rest
            order.status = OrderStatus.CANCELLED
            db.add(order)
            db.commit()
            
            await manager.send_personal_message({
                "type": "order_cancelled",
                "data": {
                    "order_id": order.id,
                    "reason": "Insufficient cash balance to complete resting limit fill"
                }
            }, user.id)
            return

        # Create trade
        self._create_trade_record(db, order.id, None, order.side, fill_qty, fill_price, principal, bond, user.id)
        
        # Update balances
        self._update_cash_balances(db, order.side, user, principal)

        # Complete the order
        order.remaining_qty = 0
        order.status = OrderStatus.FILLED
        db.add(order)
        db.commit()

        # Trigger settlement
        await settlement_service.trigger_settlement_worker()

        # Notify WebSocket
        await manager.send_personal_message({
            "type": "order_filled",
            "data": {
                "order_id": order.id,
                "ticker": bond.ticker,
                "side": order.side,
                "qty": order.quantity,
                "filled_qty": fill_qty,
                "remaining_qty": 0,
                "status": order.status,
                "avg_price": fill_price
            }
        }, user.id)

    def _create_trade_record(self, db: Session, order_id: int, rfq_id: int, side: str, qty: int, price: float, principal: float, bond: Bond, user_id: int) -> Trade:
        # If side is BUY, the user is the buyer. Seller is simulated ("STREET" / Dealer desk representation - ID 0)
        # If side is SELL, the user is the seller. Buyer is simulated (ID 0)
        # Note: We represent the market/simulated dealer using user_id = 0 (created as system account)
        buyer_id = user_id if side == "BUY" else 0
        seller_id = 0 if side == "BUY" else user_id
        
        trade = Trade(
            order_id=order_id,
            rfq_id=rfq_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            bond_id=bond.id,
            price=price,
            quantity=qty,
            principal=principal,
            settlement_status=SettlementStatus.EXECUTED,
            executed_at=datetime.utcnow()
        )
        db.add(trade)
        return trade

    def _update_cash_balances(self, db: Session, side: str, user: User, principal: float):
        if side == "BUY":
            user.cash_balance -= principal
        else:
            user.cash_balance += principal
        db.add(user)

# Instantiate the singleton matching engine
matching_engine = MatchingEngine()
