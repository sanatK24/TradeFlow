from typing import Dict, Set
from fastapi import WebSocket
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Broadcast group for public messages (e.g. market data)
        self.active_connections: Set[WebSocket] = set()
        # Map user_id to their active websocket connections
        self.user_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int = None):
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
            logger.info(f"WebSocket connected: User {user_id}")
        else:
            logger.info("WebSocket connected: Anonymous client")

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
            logger.info(f"WebSocket disconnected: User {user_id}")
        else:
            logger.info("WebSocket disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """Sends a JSON message to all active sessions of a specific user."""
        if user_id in self.user_connections:
            websockets = list(self.user_connections[user_id])
            for websocket in websockets:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending message to user {user_id}: {e}")
                    self.disconnect(websocket, user_id)

    async def broadcast(self, message: dict):
        """Broadcasts a JSON message to all connected WebSocket clients (via Redis Pub/Sub if active)."""
        from backend.app.services.redis_service import redis_service
        if redis_service.is_active and redis_service.client:
            try:
                redis_service.client.publish("websocket_broadcast", json.dumps(message))
                return
            except Exception as e:
                logger.warning(f"Failed to publish broadcast to Redis Pub/Sub: {e}")

        # Fallback to local broadcast
        await self._broadcast_local(message)

    async def _broadcast_local(self, message: dict):
        """Broadcasts a JSON message to this server node's local WebSocket connections."""
        websockets = list(self.active_connections)
        for websocket in websockets:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting message locally: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

manager = ConnectionManager()
