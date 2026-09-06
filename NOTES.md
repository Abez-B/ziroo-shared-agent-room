# Notes

Honest account of decisions, tradeoffs, what was verified vs. assumed, and what was built within the 5–6 hour timebox.

---

## 1. Context isolation — the core requirement

### How per-user agent context is scoped and kept separate
- **The Core Problem**: Two users share one room and both address `@agent ...` in the same shared message log. User A's statements, queries, and agent answers must never leak into answers given to User B, even though delivery of messages is visible in the shared room.
- **Scoping Architecture**:
  - Agent conversation threads are strictly scoped to `(room_code, user_name)`.
  - The shared room message log (`messages` list and SQLite table) stores all public events for room-wide broadcasting and UI rendering.
  - However, when an `@agent` request is triggered, the agent invocation layer is **never** passed the full room log.
  - Instead, the LLM prompt payload is constructed using *only*:
    1. **System Prompt**: Identifies the room and explicitly informs the agent it is conversing strictly with `user_name`.
    2. **Isolated History**: Only prior statements made by `user_name` (both public room messages from `user_name` and prior `@agent` responses targeted to `user_name`).
    3. **Current Query**: The latest `@agent` prompt from `user_name`.
  - Statements, queries, and agent replies associated with any other user in the room are completely excluded from the LLM prompt payload.

### Real-world scenario verified
1. **User A (Polo)**: `"i read this book called 'To Kill a Mockingbird'"`
2. **User A (Polo)**: `"@agent Who wrote the book I just mentioned?"` -> **Agent**: *"Harper Lee wrote 'To Kill a Mockingbird'."*
3. **User B (Bob)**: `"@agent Who wrote the book I just mentioned?"` -> **Agent**: *"You haven't mentioned a book yet in our conversation, Bob."* (Zero leakage from User A).
4. Verified via automated pytest (`test_context_isolation.py`) and live multi-client verification (`verify_step2_live.py`).

---

## 2. Transport choice: WebSockets vs. SSE / Polling

- **Why WebSockets**:
  - **Bidirectional Real-Time**: Both users in a room need to send messages and receive immediate broadcasts simultaneously with sub-millisecond overhead.
  - **Single Persistent Connection**: Connection state, join/leave events, live typing indicators, and message broadcasts are handled over a single `ws://.../ws/{room_code}?name={user_name}` socket.
  - **Tradeoff vs SSE/Polling**: Server-Sent Events (SSE) is one-way (server-to-client only), requiring separate HTTP POST requests for every client message, introducing HTTP handshake overhead and potential ordering ambiguity. Polling introduces artificial latency and high server load.
- **Implementation & Connection Management**:
  - `ConnectionManager` (`connection_manager.py`) tracks active client sockets per room, manages clean disconnects, and broadcasts JSON events (`chat_message`, `typing`, `room_state`, `system_notice`, `history_sync`).

---

## 3. Concurrency & Message Ordering

### What happens when both users send `@agent` messages at the exact same second
- **Deterministic Serialization**: Each `Room` instance in `backend/app/room.py` owns an `asyncio.Lock`. Inbound WebSocket messages from all clients in that room acquire this lock during message handling and agent processing.
- **Race Condition Prevention**: Even if User A and User B send `@agent` queries in the exact same millisecond, the lock serializes the execution:
  1. User A's message is logged and broadcast.
  2. Typing indicator for User A is broadcast (`is_typing: true, target_user: 'Alice'`).
  3. LLM call executes with User A's isolated context.
  4. Response is logged, broadcast, appended to User A's thread, and typing indicator is cleared (`is_typing: false`).
  5. Lock is released and User B's message is immediately processed with User B's isolated context.
- **Tradeoff**: A per-room lock is simple, predictable, and fully satisfies the concurrency requirement without distributed Redis/queue infrastructure overhead within the 5–6 hour timebox.
- **Verified**: Fired simultaneous `@agent` requests from Alice and Bob using `asyncio.gather()` in `test_concurrency.py` and `verify_step3_live.py`.

---

## 4. Persistence & Server Restart Recovery

### What is persisted vs. what is ephemeral
- **SQLite Database Schema** (`db.py` via `aiosqlite`):
  ```sql
  CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      room_code TEXT NOT NULL,
      user_name TEXT NOT NULL,
      role TEXT NOT NULL,          -- 'human' | 'agent' | 'system'
      target_user TEXT,            -- target username when role == 'agent'
      content TEXT NOT NULL,
      created_at TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_messages_room_created ON messages(room_code, created_at);
  ```
- **What is Persisted**: All room messages (human messages, agent replies with `target_user`, and system notices).
- **What is Ephemeral**: Live WebSocket connections and transient typing indicators (re-established naturally on client reconnection).
- **Server Restart Recovery**:
  - When a server boots or a room is initialized, `room.ensure_loaded()` loads all messages for `room_code` in chronological order.
  - It reconstructs the public room history AND reconstructs each user's isolated `user_threads[user_name]`.
- **Actually Verified**: `test_persistence.py` and `verify_step4_live.py` simulate a mid-session crash and reboot. After reboot, reconnected User A asked for a secret token set before the crash; the agent answered accurately, while User B's agent had no knowledge of User A's token.

---

## 5. AI Integration Hygiene & Failure Handling

### What happens when the LLM call fails, times out, or returns junk
- **Timeout Bounds**: Every agent call is bounded by a strict timeout (`AGENT_TIMEOUT_SECONDS`, default 15s) using `asyncio.timeout()`.
- **Defensive Error Handling**:
  - Handles API authentication errors (401), rate limits (429), provider outages (500/503), network drops, and empty responses.
  - Instead of hanging the room or crashing the connection, emits a visible system notice in the room: `⚠️ Agent couldn't respond: [reason]. Please try again.`
  - The typing indicator is guaranteed to be cleared via a `finally` block (`is_typing: false`).
  - WebSockets remain 100% active, and users can continue chatting immediately.
- **Multi-Provider Support**: Supports Google Gemini (`gemini-3.5-flash`), Anthropic Claude, OpenAI, and an offline `MOCK_LLM=true` mode for fast, deterministic unit testing.
- **Actually Verified**: Tested simulated timeouts and 503 provider errors in `test_failure_handling.py` and `verify_step5_live.py`.

---

## 6. Frontend Craft & UI/UX

- **Design Aesthetic**: Minimalist, Instagram-inspired monochrome dark mode (`#000000`, `#121212`, `#262626`).
- **UI States Handled**:
  1. **Join Screen**: Name & room code entry, random room generator, quick presets, validation error alerts, and connecting state.
  2. **Empty Room State**: Centered placeholder with prompt starter chips (`@agent ...`).
  3. **Message Taxonomy**:
     - *Self*: White pill bubble (`#FFFFFF` text `#000000`), right-aligned.
     - *Other Human*: Dark charcoal bubble (`#121212` / `#262626`), left-aligned with user initials avatar.
     - *AI Agent*: Structured dark card with `@agent` badge, recipient tag (`Replying to polo`), and markdown formatting.
     - *System Notices*: Clean centered status badges.
  4. **Typing Indicator**: Animated pulsing dots displaying who the agent is currently thinking for.
  5. **Input Pill**: Fast `@agent` mention chip, keyboard submit (Enter / Shift+Enter for multiline), and send button.

---

## 7. Tradeoffs & Scope-Cutting under Time Pressure

1. **Single-Node `asyncio.Lock` vs. Distributed Queue**:
   - *Decision*: Used an in-memory `asyncio.Lock` per room rather than Celery/RabbitMQ/Redis.
   - *Rationale*: A two-user shared room prototype runs on a single server instance. Introducing external distributed dependencies would add infrastructure overhead without testing evaluation criteria.
2. **Non-Streaming LLM Responses vs. Token Streaming**:
   - *Decision*: Returned the full agent response upon completion rather than streaming token-by-token.
   - *Rationale*: Guaranteed atomic locking and clean SQLite persistence without partial chunk reconciliation or race conditions.
3. **Simple Session Identity vs. Full Auth (JWT/OAuth)**:
   - *Decision*: Simple name + room code without passwords or user databases.
   - *Rationale*: Kept setup zero-friction for evaluation, allowing two browser tabs to act as User A and User B immediately.

---

## 8. What I Verified vs. What I'm Assuming

- **Verified (Tested & Proven)**:
  - Multi-client WebSocket join, live broadcast, and state synchronization across multiple tabs.
  - Per-user context isolation with zero memory leakage between users.
  - Simultaneous `@agent` queries serialized without race conditions or memory corruption.
  - SQLite persistence and state recovery across server process restarts.
  - LLM failure degradation (timeouts, provider errors) with system alerts and socket preservation.
  - Offline automated test suite (6/6 tests passing in pytest in <18s).
- **Assumed (Not Tested)**:
  - Horizontal scaling across multiple server instances (would require Redis Pub/Sub for WebSockets).
  - Rooms with 100+ concurrent active participants.

---

## 9. What I'd Improve with More Time

1. **Token-Aware Context Truncation**: Add sliding window or summarization for long user threads exceeding 100+ turns.
2. **Token-by-Token Response Streaming**: Broadcast incremental `agent_chunk` WebSocket events for lower perceived latency.
3. **Ephemeral Presence Indicators**: Real-time user typing indicators ("Polo is typing...").
4. **Room Memory Modes**: Toggleable room configuration allowing users to choose between strictly private per-user context vs. a communal shared agent memory.

---

## 10. Time Spent Breakdown (~5–6 Hour Timebox)

- **0:00 – 0:45**: Architecture design, project scaffolding, and Step 1 (FastAPI WebSocket transport + broadcast).
- **0:45 – 1:45**: Step 2 (Context isolation scoping engine, user history tracking, `@agent` detection, multi-provider LLM integration, and two-user non-leakage verification).
- **1:45 – 2:30**: Step 3 (Concurrency serialization via per-room `asyncio.Lock`, atomic queue processing, and parallel request testing).
- **2:30 – 3:15**: Step 4 (SQLite persistence schema with `aiosqlite`, thread recovery on server reboot, mid-session restart test suite).
- **3:15 – 4:00**: Step 5 (Defensive failure handling, timeout bounds, upstream error degradation, and live simulation).
- **4:00 – 5:15**: Step 6 (Svelte frontend build, stores, Instagram-inspired monochrome dark mode styling, DM bubble taxonomy, typing indicators, and empty states).
- **5:15 – 5:45**: Step 7 (Documentation in `NOTES.md` and `README.md`, full test suite verification).


