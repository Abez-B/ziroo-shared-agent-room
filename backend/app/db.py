import os
import aiosqlite
import logging
from typing import List, Optional
try:
    from app.models import ChatMessage
except ImportError:
    from backend.app.models import ChatMessage

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "./room.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    room_code TEXT NOT NULL,
    user_name TEXT NOT NULL,
    role TEXT NOT NULL,
    target_user TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_room_code ON messages(room_code);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
"""

async def init_db(db_path: Optional[str] = None):
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    async with aiosqlite.connect(path) as db:
        await db.executescript(CREATE_TABLE_SQL)
        await db.commit()
    logger.info(f"Database initialized at {path}")

async def save_message(msg: ChatMessage, db_path: Optional[str] = None):
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            INSERT INTO messages (id, room_code, user_name, role, target_user, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg.id, msg.room_code, msg.user_name, msg.role, msg.target_user, msg.content, msg.created_at)
        )
        await db.commit()

async def load_room_messages(room_code: str, db_path: Optional[str] = None) -> List[ChatMessage]:
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    if not os.path.exists(path):
        return []

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, room_code, user_name, role, target_user, content, created_at FROM messages WHERE room_code = ? ORDER BY created_at ASC, rowid ASC",
            (room_code,)
        ) as cursor:
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                messages.append(ChatMessage(
                    id=row["id"],
                    room_code=row["room_code"],
                    user_name=row["user_name"],
                    role=row["role"],
                    target_user=row["target_user"],
                    content=row["content"],
                    created_at=row["created_at"]
                ))
            return messages
