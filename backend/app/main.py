import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User
from backend.app.routes import auth, bonds, orders, rfqs, trades, analytics
from backend.app.websocket.connection_manager import manager
from backend.app.services.market_data_simulator import market_simulator
from backend.app.services.settlement_service import settlement_service
from backend.app.services.rfq_manager import rfq_manager
from backend.app.services.redis_service import redis_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tradeflow")

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For simulation purposes, allow all. In production, restrict to React domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(bonds.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(rfqs.router, prefix=settings.API_V1_STR)
app.include_router(trades.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_event():
    logger.info("Starting TradeFlow application services...")
    
    # 1. Create database tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed bonds table and initialize books
    db = SessionLocal()
    market_simulator.seed_bonds(db)
    
    # Auto-seed system bot (id=0) on start
    system_user = db.query(User).filter(User.id == 0).first()
    if not system_user:
        try:
            from backend.app.routes.auth import get_password_hash
            bot = User(
                id=0,
                username="STREET_LIQUIDITY",
                password_hash=get_password_hash("streetliquiditypass123"),
                cash_balance=1000000000000.0
            )
            db.add(bot)
            db.commit()
        except Exception as e:
            logger.warning(f"Error seeding street liquidity user: {e}")
            db.rollback()
    db.close()
    
    # 3. Start background simulators
    market_simulator.start()
    settlement_service.start()
    rfq_manager.start()
    
    # 4. Start Redis pub/sub listener (if Redis is active)
    redis_service.start_pubsub_listener()

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Stopping TradeFlow application services...")
    market_simulator.stop()
    settlement_service.stop()
    rfq_manager.stop()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Real-time updates socket channel."""
    user_id = None
    db = SessionLocal()
    
    # Decode token from query param if available to identify user connection
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username = payload.get("sub")
            if username:
                user = db.query(User).filter(User.username == username).first()
                if user:
                    user_id = user.id
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
    
    db.close()
    
    # Accept and register WebSocket connection
    await manager.connect(websocket, user_id)
    
    try:
        # Loop to keep connection open and listen for client signals if any
        while True:
            # Receive client messages (currently we just echo or ignore, 
            # as most actions go through HTTP endpoints for validation)
            data = await websocket.receive_text()
            # simple ping-pong implementation
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.warning(f"WebSocket connection error on user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

@app.get("/")
def read_root():
    return {"message": "TradeFlow Electronic Bond Trading Desk API is online"}
