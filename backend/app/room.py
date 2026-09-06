import asyncio
import logging
from typing import Dict, List, Optional
try:
    from app.models import ChatMessage
    from app.connection_manager import manager
    from app.agent import agent_service, is_agent_addressed, clean_agent_prompt
    from app.db import save_message, load_room_messages
except ImportError:
    from backend.app.models import ChatMessage
    from backend.app.connection_manager import manager
    from backend.app.agent import agent_service, is_agent_addressed, clean_agent_prompt
    from backend.app.db import save_message, load_room_messages

logger = logging.getLogger(__name__)

class Room:
    def __init__(self, room_code: str):
        self.room_code = room_code
        self.lock = asyncio.Lock()
        self.messages: List[ChatMessage] = []
        # Context Isolation: Mapping user_name -> isolated list of {"role": "user"|"assistant", "content": ...}
        self.user_threads: Dict[str, List[Dict[str, str]]] = {}
        self.loaded_from_db = False

    async def ensure_loaded(self):
        """Loads room history and reconstructs per-user agent threads from SQLite."""
        if self.loaded_from_db:
            return
        async with self.lock:
            if self.loaded_from_db:
                return
            db_messages = await load_room_messages(self.room_code)
            self.messages = db_messages
            self.user_threads = {}
            for msg in db_messages:
                if msg.role == "human":
                    if msg.user_name not in self.user_threads:
                        self.user_threads[msg.user_name] = []
                    self.user_threads[msg.user_name].append({
                        "role": "user",
                        "content": clean_agent_prompt(msg.content)
                    })
                elif msg.role == "agent" and msg.target_user:
                    if msg.target_user not in self.user_threads:
                        self.user_threads[msg.target_user] = []
                    self.user_threads[msg.target_user].append({
                        "role": "assistant",
                        "content": msg.content
                    })
            self.loaded_from_db = True
            logger.info(f"Loaded room '{self.room_code}' from DB with {len(self.messages)} messages.")

    async def handle_user_message(self, user_name: str, content: str) -> ChatMessage:
        await self.ensure_loaded()
        async with self.lock:
            # 1. Create and persist the human message
            human_msg = ChatMessage(
                room_code=self.room_code,
                user_name=user_name,
                role="human",
                content=content
            )
            self.messages.append(human_msg)
            await save_message(human_msg)

            # Record in user's isolated conversation thread
            if user_name not in self.user_threads:
                self.user_threads[user_name] = []

            # 2. Broadcast the human message to everyone in the room
            await manager.broadcast_json(
                self.room_code,
                {
                    "type": "chat_message",
                    "payload": human_msg.model_dump()
                }
            )

            # 3. Check if @agent is addressed
            if is_agent_addressed(content):
                await self._process_agent_call(user_name, content)
            else:
                # Append normal chat to user's own thread so agent understands user's prior context
                self.user_threads[user_name].append({
                    "role": "user",
                    "content": content
                })

            return human_msg

    async def _process_agent_call(self, user_name: str, content: str):
        # Notify room that agent is thinking for this specific user
        await manager.broadcast_json(
            self.room_code,
            {
                "type": "typing",
                "payload": {
                    "user_name": "agent",
                    "target_user": user_name,
                    "is_typing": True
                }
            }
        )

        try:
            # Context Isolation: Retrieve ONLY this user's conversation thread
            user_history = self.user_threads.get(user_name, [])

            # Call agent with this user's isolated history
            reply = await agent_service.generate_response(
                user_name=user_name,
                room_code=self.room_code,
                prompt=content,
                user_history=user_history
            )

            # Update ONLY this user's thread
            if user_name not in self.user_threads:
                self.user_threads[user_name] = []
            
            cleaned_prompt = clean_agent_prompt(content)
            self.user_threads[user_name].append({"role": "user", "content": cleaned_prompt})
            self.user_threads[user_name].append({"role": "assistant", "content": reply})

            # Create agent message
            agent_msg = ChatMessage(
                room_code=self.room_code,
                user_name="agent",
                role="agent",
                target_user=user_name,
                content=reply
            )
            self.messages.append(agent_msg)
            await save_message(agent_msg)

            # Broadcast agent reply to the room
            await manager.broadcast_json(
                self.room_code,
                {
                    "type": "chat_message",
                    "payload": agent_msg.model_dump()
                }
            )

        except Exception as exc:
            logger.exception(f"Error calling agent for {user_name} in {self.room_code}: {exc}")
            err_msg = ChatMessage(
                room_code=self.room_code,
                user_name="system",
                role="system",
                target_user=user_name,
                content=f"⚠️ Agent couldn't respond: {str(exc) if str(exc) else 'Unknown error'}. Please try again."
            )
            self.messages.append(err_msg)
            await save_message(err_msg)
            await manager.broadcast_json(
                self.room_code,
                {
                    "type": "chat_message",
                    "payload": err_msg.model_dump()
                }
            )
        finally:
            # Clear typing indicator
            await manager.broadcast_json(
                self.room_code,
                {
                    "type": "typing",
                    "payload": {
                        "user_name": "agent",
                        "target_user": user_name,
                        "is_typing": False
                    }
                }
            )

    def get_history(self) -> List[dict]:
        return [msg.model_dump() for msg in self.messages]

    def get_user_thread(self, user_name: str) -> List[Dict[str, str]]:
        return list(self.user_threads.get(user_name, []))


_active_rooms: Dict[str, Room] = {}

def get_or_create_room(room_code: str) -> Room:
    if room_code not in _active_rooms:
        _active_rooms[room_code] = Room(room_code)
    return _active_rooms[room_code]

def reset_all_rooms():
    """Helper for test suites."""
    _active_rooms.clear()
