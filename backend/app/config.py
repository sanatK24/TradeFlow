import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env configuration
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "TradeFlow Electronic Trading Simulator"
    API_V1_STR: str = "/api/v1"
    
    # DB Configuration: fallback to SQLite file locally
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tradeflow.db")
    
    # Redis Configuration: fallback to in-memory mock if empty/unavailable
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkeytradeflowsimula123")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Sim speed multiplier (e.g. 1.0 = standard, higher = faster tick rates if needed)
    SIMULATION_SPEED: float = 1.0

    class Config:
        case_sensitive = True

settings = Settings()
