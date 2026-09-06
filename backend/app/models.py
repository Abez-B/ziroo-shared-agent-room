from datetime import datetime, timezone
import uuid
from typing import Optional, Literal
from pydantic import BaseModel, Field

RoleType = Literal["human", "agent", "system"]

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_code: str
    user_name: str
    role: RoleType
    content: str
    target_user: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WSIncomingMessage(BaseModel):
    content: str

class WSEvent(BaseModel):
    type: Literal["chat_message", "system_notice", "typing", "history_sync", "room_state"]
    payload: dict
