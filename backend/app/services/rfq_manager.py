import asyncio
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models import RFQ, Quote, Bond, User, RfqStatus, Trade, SettlementStatus
from backend.app.services.market_data_simulator import market_simulator, calculate_ytm, calculate_years_to_maturity
from backend.app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

# List of institutional clients that request quotes in Dealer Mode
INSTITUTIONAL_CLIENTS = ["BlackRock", "Vanguard", "PIMCO", "Fidelity", "State Street", "AllianceBernstein"]
# List of dealer counterparties in Client Mode
DEALER_NAMES = ["Goldman Sachs", "JPMorgan Chase", "Barclays", "Morgan Stanley", "Citi"]

class RfqManager:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._dealer_rfq_loop())
        logger.info("RFQ Manager background loop started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("RFQ Manager background loop stopped.")

    async def generate_dealer_quotes_for_client_rfq(self, rfq_id: int):
        """Asynchronously simulates dealer quote replies 1-3 seconds after a client submits an RFQ."""
        await asyncio.sleep(random.uniform(1.0, 2.5))
        
        db = SessionLocal()
        try:
            rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
            if not rfq or rfq.status != RfqStatus.REQUESTED:
                db.close()
                return

            bond = db.query(Bond).filter(Bond.id == rfq.bond_id).first()
            if not bond:
                db.close()
                return

            years = calculate_years_to_maturity(bond.maturity_date)
            mid_price = bond.last_price
            
            # Generate quotes from 3 random dealers
            dealers = random.sample(DEALER_NAMES, 3)
            quotes = []
            
            for dealer in dealers:
                # Dealer spreads. If client wants to BUY, dealers offer asks (higher than mid).
                # If client wants to SELL, dealers offer bids (lower than mid).
                if rfq.side == "BUY":
                    # Dealer offers selling price: mid + markup
                    price = round(mid_price + random.uniform(0.02, 0.12), 3)
                else:
                    # Dealer offers buying price: mid - markdown
                    price = round(mid_price - random.uniform(0.02, 0.12), 3)
                
                ytm = calculate_ytm(price, bond.coupon, years)
                
                quote = Quote(
                    rfq_id=rfq.id,
                    dealer_name=dealer,
                    price=price,
                    yield_pct=ytm,
                    expires_at=rfq.expires_at,
                    created_at=datetime.utcnow()
                )
                db.add(quote)
                quotes.append(quote)
            
            rfq.status = RfqStatus.QUOTED
            db.add(rfq)
            db.commit()

            # Broadcast quote arrival to client
            quotes_data = [
                {
                    "quote_id": q.id,
                    "dealer_name": q.dealer_name,
                    "price": q.price,
                    "yield_pct": q.yield_pct,
                    "expires_at": q.expires_at.isoformat()
                }
                for q in quotes
            ]

            await manager.send_personal_message({
                "type": "rfq_quotes_received",
                "data": {
                    "rfq_id": rfq.id,
                    "ticker": bond.ticker,
                    "side": rfq.side,
                    "qty": rfq.quantity,
                    "quotes": quotes_data,
                    "expires_at": rfq.expires_at.isoformat()
                }
            }, rfq.client_id)

        except Exception as e:
            logger.error(f"Error generating dealer quotes: {e}", exc_info=True)
        finally:
            db.close()

    async def _dealer_rfq_loop(self):
        """Periodically spawns incoming RFQs for the user to price (Dealer Mode)."""
        await asyncio.sleep(10.0) # wait for startup
        while self._running:
            db = SessionLocal()
            try:
                # Only spawn if there are active users to receive it
                active_user_ids = list(manager.user_connections.keys())
                if active_user_ids:
                    bonds = db.query(Bond).all()
                    if bonds:
                        # Pick a random bond, quantity and side
                        bond = random.choice(bonds)
                        side = random.choice(["BUY", "SELL"]) # Client's side (i.e. client wants to BUY/SELL)
                        # Bonds trade in size, e.g. 5,000, 10,000 contracts ($5M, $10M)
                        qty = random.choice([1000, 2000, 5000, 10000])
                        client_name = random.choice(INSTITUTIONAL_CLIENTS)
                        
                        # Expiration is short (15 seconds) to make it exciting
                        duration_sec = 18
                        expires_at = datetime.utcnow() + timedelta(seconds=duration_sec)
                        
                        # System user (ID 0) acts as client, but we tag with a custom client name in descriptions.
                        # We will associate the client RFQ with user ID 0 (representing client bots).
                        rfq = RFQ(
                            client_id=0, # Bot client
                            bond_id=bond.id,
                            side=side,
                            quantity=qty,
                            status=RfqStatus.REQUESTED,
                            expires_at=expires_at,
                            created_at=datetime.utcnow()
                        )
                        db.add(rfq)
                        db.commit()
                        
                        # Broadcast incoming RFQ to all active users (acting as dealers)
                        await manager.broadcast({
                            "type": "incoming_rfq_alert",
                            "data": {
                                "rfq_id": rfq.id,
                                "client_name": client_name,
                                "ticker": bond.ticker,
                                "side": side,  # BUY = Client wants to buy (User must SELL)
                                "qty": qty,
                                "expires_at": expires_at.isoformat(),
                                "duration_seconds": duration_sec
                            }
                        })
                        
                        # Spawn background task to check for expiration
                        asyncio.create_task(self._handle_rfq_expiration(rfq.id, client_name))
                
                db.close()
            except Exception as e:
                logger.error(f"Error in Dealer RFQ Loop: {e}", exc_info=True)
                
            # Spawn a new RFQ every 25 seconds
            await asyncio.sleep(25.0)

    async def _handle_rfq_expiration(self, rfq_id: int, client_name: str):
        """Waits for RFQ expiry, then evaluates quotes if not already processed."""
        # Add 0.5s padding
        await asyncio.sleep(18.5)
        
        db = SessionLocal()
        try:
            rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
            if not rfq or rfq.status in [RfqStatus.ACCEPTED, RfqStatus.REJECTED, RfqStatus.EXPIRED]:
                db.close()
                return

            # If no quotes were submitted, expire
            quotes = db.query(Quote).filter(Quote.rfq_id == rfq.id).all()
            if not quotes:
                rfq.status = RfqStatus.EXPIRED
                db.add(rfq)
                db.commit()
                await manager.broadcast({
                    "type": "rfq_expired",
                    "data": {
                        "rfq_id": rfq.id,
                        "client_name": client_name
                    }
                })
                db.close()
                return

            # Evaluate quotes. Let's execute the client's decision!
            bond = db.query(Bond).filter(Bond.id == rfq.bond_id).first()
            
            # Client decision logic:
            # - If Client wants to BUY: client accepts the lowest price quote.
            # - If Client wants to SELL: client accepts the highest price quote.
            # However, the client will only accept quotes that are close to the fair market mid price.
            # If the best price is more than 0.20 off the market price, client rejects all as "out of market".
            mid = bond.last_price
            
            # Sort quotes
            if rfq.side == "BUY": # Client is buying, wants lowest price
                sorted_quotes = sorted(quotes, key=lambda q: q.price)
                best_quote = sorted_quotes[0]
                market_limit = mid + 0.15 # Max price client is willing to pay
                is_acceptable = best_quote.price <= market_limit
            else: # Client is selling, wants highest price
                sorted_quotes = sorted(quotes, key=lambda q: q.price, reverse=True)
                best_quote = sorted_quotes[0]
                market_limit = mid - 0.15 # Min price client is willing to accept
                is_acceptable = best_quote.price >= market_limit

            if is_acceptable:
                rfq.status = RfqStatus.ACCEPTED
                db.add(rfq)
                
                # Check who won
                winner_dealer = best_quote.dealer_name
                # Check if a user submitted this quote
                # We identify user quotes by prefix "User_" (e.g. "User_1")
                is_user_win = winner_dealer.startswith("User_")
                
                user_id_won = int(winner_dealer.split("_")[1]) if is_user_win else None
                
                # Create trade
                # If Client wants to BUY, the winner is selling. 
                # Bot (client_id 0) is buyer, Winner is seller.
                buyer_id = 0
                seller_id = user_id_won if is_user_win else 0 # 0 represents outside dealer/street
                
                if rfq.side == "SELL":
                    # Client wants to SELL, winner is buying.
                    buyer_id = user_id_won if is_user_win else 0
                    seller_id = 0
                
                principal = rfq.quantity * best_quote.price * (bond.face_value / 100.0)
                
                trade = Trade(
                    rfq_id=rfq.id,
                    buyer_id=buyer_id,
                    seller_id=seller_id,
                    bond_id=bond.id,
                    price=best_quote.price,
                    quantity=rfq.quantity,
                    principal=principal,
                    settlement_status=SettlementStatus.EXECUTED,
                    executed_at=datetime.utcnow()
                )
                db.add(trade)

                # Adjust user balances if user won
                if is_user_win:
                    user = db.query(User).filter(User.id == user_id_won).first()
                    if user:
                        if rfq.side == "BUY":
                            # Client bought from User. User sells bonds, receives cash principal.
                            user.cash_balance += principal
                        else:
                            # Client sold to User. User buys bonds, pays cash principal.
                            user.cash_balance -= principal
                        db.add(user)

                db.commit()

                # Trigger settlement check
                from backend.app.services.settlement_service import settlement_service
                await settlement_service.trigger_settlement_worker()

                # Broadcast result
                await manager.broadcast({
                    "type": "rfq_accepted",
                    "data": {
                        "rfq_id": rfq.id,
                        "client_name": client_name,
                        "winner": "You" if is_user_win else winner_dealer,
                        "price": best_quote.price,
                        "ticker": bond.ticker,
                        "side": rfq.side,
                        "qty": rfq.quantity,
                        "user_won": is_user_win,
                        "user_id": user_id_won
                    }
                })
            else:
                rfq.status = RfqStatus.REJECTED
                db.add(rfq)
                db.commit()
                
                await manager.broadcast({
                    "type": "rfq_rejected",
                    "data": {
                        "rfq_id": rfq.id,
                        "client_name": client_name,
                        "reason": "All quotes were out of market bounds."
                    }
                })
        except Exception as e:
            logger.error(f"Error handling RFQ expiration: {e}", exc_info=True)
        finally:
            db.close()

    async def submit_user_quote(self, db: Session, rfq_id: int, user_id: int, price: float):
        """Allows the user to submit a price quote for a active client RFQ (Dealer Mode)."""
        rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
        if not rfq:
            return {"status": "error", "message": "RFQ not found"}

        if rfq.status != RfqStatus.REQUESTED or datetime.utcnow() > rfq.expires_at:
            return {"status": "error", "message": "RFQ is no longer active"}

        bond = db.query(Bond).filter(Bond.id == rfq.bond_id).first()
        years = calculate_years_to_maturity(bond.maturity_date)
        ytm = calculate_ytm(price, bond.coupon, years)

        # 1. Save user quote
        user_quote = Quote(
            rfq_id=rfq.id,
            dealer_name=f"User_{user_id}",
            price=price,
            yield_pct=ytm,
            expires_at=rfq.expires_at,
            created_at=datetime.utcnow()
        )
        db.add(user_quote)

        # 2. Simulate competing dealer quotes for this RFQ in the database
        # This makes it a real auction where the user competes with Wall Street dealers!
        mid = bond.last_price
        other_dealers = random.sample(DEALER_NAMES, 2)
        
        for dealer in other_dealers:
            if rfq.side == "BUY": # Client is buying, dealers quote selling prices (asks)
                # Competitor quotes mid + markup
                comp_price = round(mid + random.uniform(0.01, 0.15), 3)
            else: # Client is selling, dealers quote buying prices (bids)
                # Competitor quotes mid - markdown
                comp_price = round(mid - random.uniform(0.01, 0.15), 3)
                
            comp_ytm = calculate_ytm(comp_price, bond.coupon, years)
            
            comp_quote = Quote(
                rfq_id=rfq.id,
                dealer_name=dealer,
                price=comp_price,
                yield_pct=comp_ytm,
                expires_at=rfq.expires_at,
                created_at=datetime.utcnow()
            )
            db.add(comp_quote)

        db.commit()

        # Notify other users/WS that quotes are submitted
        await manager.broadcast({
            "type": "rfq_quote_submitted",
            "data": {
                "rfq_id": rfq.id,
                "dealer_name": "You"
            }
        })
        
        return {"status": "success", "message": "Quote submitted successfully"}

# Instantiate singleton RFQ manager
rfq_manager = RfqManager()
