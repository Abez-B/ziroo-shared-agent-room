import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
try:
    from app.connection_manager import manager
    from app.room import get_or_create_room
    from app.models import ChatMessage
    from app.db import init_db
except ImportError:
    from backend.app.connection_manager import manager
    from backend.app.room import get_or_create_room
    from backend.app.models import ChatMessage
    from backend.app.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ziroo-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLite database...")
    await init_db()
    logger.info("Starting Ziroo Backend...")
    yield
    logger.info("Shutting down Ziroo Backend...")

app = FastAPI(title="Ziroo Shared Agent Room API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/{room_code}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    name: str = Query(..., description="The user's display name")
):
    user_name = name.strip()
    if not user_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Username cannot be empty")
        return

    room = get_or_create_room(room_code)
    await room.ensure_loaded()
    await manager.connect(room_code, user_name, websocket)

    try:
        # Send initial sync payload to the newly connected user
        history = room.get_history()
        active_users = manager.get_active_users(room_code)
        await websocket.send_json({
            "type": "history_sync",
            "payload": {
                "room_code": room_code,
                "messages": history,
                "active_users": active_users
            }
        })

        # Broadcast join notice and updated user list to everyone in the room
        await manager.broadcast_json(room_code, {
            "type": "system_notice",
            "payload": {
                "content": f"{user_name} joined the room."
            }
        })
        await manager.broadcast_json(room_code, {
            "type": "room_state",
            "payload": {
                "active_users": manager.get_active_users(room_code)
            }
        })

        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                data = {"content": raw_text}

            content = data.get("content", "").strip()
            if not content:
                continue

            await room.handle_user_message(user_name, content)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {user_name} in {room_code}")
    except Exception as exc:
        logger.exception(f"Unexpected error in websocket loop for {user_name}: {exc}")
    finally:
        manager.disconnect(room_code, user_name, websocket)
        await manager.broadcast_json(room_code, {
            "type": "system_notice",
            "payload": {
                "content": f"{user_name} left the room."
            }
        })
        await manager.broadcast_json(room_code, {
            "type": "room_state",
            "payload": {
                "active_users": manager.get_active_users(room_code)
            }
        })

# Mount frontend build directory if it exists
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

