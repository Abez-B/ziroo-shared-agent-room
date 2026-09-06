import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages live WebSocket connections keyed by room_code.
    Tracks active connections per user to enable room broadcasting
    and individual notifications.
    """
    def __init__(self):
        # room_code -> dict of user_name -> set of WebSockets (to support multiple tabs/reconnects)
        self.rooms: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, room_code: str, user_name: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.rooms:
            self.rooms[room_code] = {}
        if user_name not in self.rooms[room_code]:
            self.rooms[room_code][user_name] = set()
        self.rooms[room_code][user_name].add(websocket)
        logger.info(f"User '{user_name}' connected to room '{room_code}'.")

    def disconnect(self, room_code: str, user_name: str, websocket: WebSocket):
        if room_code in self.rooms and user_name in self.rooms[room_code]:
            self.rooms[room_code][user_name].discard(websocket)
            if not self.rooms[room_code][user_name]:
                del self.rooms[room_code][user_name]
            if not self.rooms[room_code]:
                del self.rooms[room_code]
        logger.info(f"User '{user_name}' disconnected from room '{room_code}'.")

    async def broadcast_json(self, room_code: str, data: dict):
        if room_code not in self.rooms:
            return

        dead_connections = []
        for user_name, sockets in list(self.rooms[room_code].items()):
            for ws in list(sockets):
                try:
                    await ws.send_json(data)
                except Exception as exc:
                    logger.warning(f"Error sending to {user_name} in {room_code}: {exc}")
                    dead_connections.append((user_name, ws))

        for user_name, ws in dead_connections:
            self.disconnect(room_code, user_name, ws)

    def get_active_users(self, room_code: str) -> List[str]:
        if room_code not in self.rooms:
            return []
        return list(self.rooms[room_code].keys())

manager = ConnectionManager()
