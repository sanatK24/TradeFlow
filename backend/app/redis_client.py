import logging
import json
from typing import Any, Optional, Dict
from backend.app.config import settings

logger = logging.getLogger(__name__)

class MockRedisClient:
    """An in-memory mock Redis client used as a fallback for local execution."""
    def __init__(self):
        self._store: Dict[str, str] = {}
        logger.info("Initializing in-memory Mock Redis Client (Fallback Mode)")

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = str(value)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def publish(self, channel: str, message: str) -> int:
        # In mock mode, we bypass Redis pub/sub and use direct websocket broadcasts
        # in our WebSocket manager. This mock publishes to nowhere and returns 0.
        return 0

    class MockPubSub:
        async def subscribe(self, *args, **kwargs):
            pass
        async def listen(self):
            yield {"type": "subscribe", "channel": "mock", "data": 1}

    def pubsub(self):
        return self.MockPubSub()

# Try to initialize real Redis, otherwise fallback to Mock
redis_client = None

if settings.REDIS_URL:
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis at {settings.REDIS_URL}. Falling back to Mock. Error: {e}")
        redis_client = MockRedisClient()
else:
    redis_client = MockRedisClient()
