import json
import logging
import os
import redis
from typing import Any, Optional

logger = logging.getLogger("tradeflow.redis")

class RedisService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
        self.is_active = False
        self._mock_cache = {}

        self.initialize_connection()

    def initialize_connection(self):
        """Attempts to connect to Redis, logs status, and sets active flag."""
        try:
            logger.info(f"Connecting to Redis at {self.redis_url}...")
            self.client = redis.Redis.from_url(self.redis_url, socket_timeout=2.0)
            # Test connection with a ping
            self.client.ping()
            self.is_active = True
            logger.info("Successfully connected to Redis. Redis features enabled.")
        except Exception as e:
            self.is_active = False
            self.client = None
            logger.warning(f"Could not connect to Redis: {e}. Falling back to In-Memory simulation mode.")

    def set_cache(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """Sets a key value pair in cache. Automatically serializes dicts/lists to JSON."""
        serialized_val = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if self.is_active and self.client:
            try:
                self.client.set(key, serialized_val, ex=expire_seconds)
                return True
            except Exception as e:
                logger.warning(f"Redis write error for key '{key}': {e}")
                # Fall through to mock cache on write failure
        
        self._mock_cache[key] = value
        return True

    def get_cache(self, key: str, default: Any = None) -> Any:
        """Gets a value from cache. Deserializes JSON arrays or objects if found."""
        if self.is_active and self.client:
            try:
                val = self.client.get(key)
                if val is not None:
                    decoded = val.decode("utf-8")
                    try:
                        return json.loads(decoded)
                    except ValueError:
                        return decoded
            except Exception as e:
                logger.warning(f"Redis read error for key '{key}': {e}")
                # Fall through to mock cache on read failure

        return self._mock_cache.get(key, default)

    async def publish(self, channel: str, message: dict):
        """Publishes a message to a Redis Pub/Sub channel. Falls back to direct WebSocket broadcast if Redis is offline."""
        if self.is_active and self.client:
            try:
                # Convert dict to JSON string for transmission
                self.client.publish(channel, json.dumps(message))
                return
            except Exception as e:
                logger.warning(f"Redis publish error: {e}")

        # Fallback: broadcast directly to all local WebSocket connections
        from backend.app.websocket.connection_manager import manager
        await manager.broadcast(message)

    def start_pubsub_listener(self):
        """Starts a background task subscribing to pub/sub channels if Redis is active."""
        if not self.is_active or not self.client:
            return None

        import asyncio
        async def listen():
            pubsub = self.client.pubsub()
            pubsub.subscribe("websocket_broadcast")
            logger.info("Started Redis Pub/Sub WebSocket broadcast listener.")
            
            from backend.app.websocket.connection_manager import manager
            while self.is_active:
                try:
                    # Non-blocking check for messages (yields control to event loop)
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                    if message:
                        data_str = message['data'].decode('utf-8')
                        data = json.loads(data_str)
                        # Broadcast the parsed message to all connected clients on this node locally
                        await manager._broadcast_local(data)
                except Exception as e:
                    logger.warning(f"Error in Redis Pub/Sub listener: {e}")
                await asyncio.sleep(0.05)

        return asyncio.create_task(listen())

redis_service = RedisService()
