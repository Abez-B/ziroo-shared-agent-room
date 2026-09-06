<div align="center">

# ⚡ Ziroo Shared Agent Room

**A real-time multiplayer chat room with an AI participant and strictly isolated per-user conversation memory.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/Transport-WebSockets-010101?style=for-the-badge&logo=socketdotio&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Svelte](https://img.shields.io/badge/Frontend-Svelte-FF3E00?style=for-the-badge&logo=svelte&logoColor=white)](https://svelte.dev)
[![SQLite](https://img.shields.io/badge/Persistence-SQLite%20%2B%20aiosqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Gemini](https://img.shields.io/badge/AI%20Model-Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Pytest](https://img.shields.io/badge/Tests-6%2F6%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-white?style=for-the-badge)](LICENSE)

<br/>

[Live Portfolio](https://bharath.is-cool.dev/) • [Resume](https://kuruk.am/bharathresume) • [Architecture Notes](NOTES.md) • [Assignment Brief](AGENTS.md)

</div>

---

## 📖 Overview

In modern collaborative workspaces, multiple users share the same channel while addressing an AI assistant (`@agent ...`). 

**The Core Challenge**: When User A and User B chat in the same room and both invoke `@agent`, the AI must maintain **two strictly independent conversation threads**. User A's private context, past queries, and data must **never** leak into the answers given to User B—even though all messages arrive and are broadcast live in the same shared stream.

This repository implements a full-stack, production-grade prototype resolving this core requirement with deterministic concurrency, SQLite persistence, and an Instagram-inspired monochrome dark UI.

---

## ✨ Features

- 🔒 **Zero Context Leakage**: Memory threads are strictly partitioned by `(room_code, user_name)`. The agent is provided only with that user's historical queries and responses.
- ⚡ **Real-Time WebSocket Transport**: Bi-directional, low-latency socket communication for multi-client chat, presence, typing indicators, and room synchronization.
- 🛡️ **Deterministic Concurrency**: Per-room `asyncio.Lock` serializes concurrent `@agent` invocations without race conditions or memory interleaving.
- 💾 **Mid-Session Restart Persistence**: SQLite schema (`aiosqlite`) persists all room events; server reboots automatically reconstruct public logs and isolated per-user memory threads.
- ⚠️ **Defensive Failure Degradation**: Timeouts (`asyncio.timeout(15.0)`), upstream error handling (401/429/503), and visible in-room alerts keep sockets responsive without hanging.
- 🖤 **Instagram-Inspired Monochrome Dark UI**: Minimalist black & charcoal aesthetic (`#000000`, `#121212`, `#262626`), markdown formatting with code blocks, one-click copy, and live connection status indicators.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                   SHARED ROOM STREAM                   │
│  [User A: "I read 'To Kill a Mockingbird'"]           │
│  [User B: "@agent Who wrote the book I mentioned?"]    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend (WebSocket)                │
│  • ConnectionManager: Tracks live sockets per room     │
│  • Room Lock (asyncio.Lock): Serializes incoming calls │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐
│   User A Thread Memory  │ │   User B Thread Memory  │
│  • "I read Mockingbird" │ │  • (Empty / No context) │
└────────────┬────────────┘ └────────────┬────────────┘
             │                           │
             ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐
│ Agent Response to A:    │ │ Agent Response to B:    │
│ "Harper Lee wrote..."   │ │ "You haven't mentioned  │
│                         │ │  a book yet, User B."   │
└─────────────────────────┘ └─────────────────────────┘
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- An API Key for Gemini, Anthropic, or OpenAI (or run offline with `MOCK_LLM=true`)

### 1. Clone & Setup Repository

```bash
git clone https://github.com/Abez-B/ziroo-shared-agent-room.git
cd ziroo-shared-agent-room
```

### 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

### 4. Run Development Servers

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **`http://localhost:5173`** in two separate browser tabs with different names (e.g., `Polo` and `Bob`) and the same room code to test real-time collaboration live!

---

## 🧪 Automated Test Suite

The test suite validates all 6 core requirements across concurrency, context isolation, persistence, failure handling, and socket broadcasting.

```bash
PYTHONPATH=. backend/.venv/bin/pytest backend/tests/ -v
```

### Test Results (100% Pass Rate):
```
============================= test session starts ==============================
platform linux -- Python 3.14.x, pytest-9.1.1
rootdir: /home/abe-z/Projects/ziroo-shared-agent-room

backend/tests/test_concurrency.py::test_concurrent_agent_calls_serialized PASSED [ 16%]
backend/tests/test_context_isolation.py::test_context_isolation_between_two_users PASSED [ 33%]
backend/tests/test_failure_handling.py::test_agent_timeout_degrades_gracefully PASSED [ 50%]
backend/tests/test_failure_handling.py::test_agent_upstream_error_degrades_gracefully PASSED [ 66%]
backend/tests/test_persistence.py::test_sqlite_persistence_and_server_restart PASSED [ 83%]
backend/tests/test_ws_broadcast.py::test_websocket_broadcast_between_two_users PASSED [100%]

============================== 6 passed in 17.84s ==============================
```

---

## ⚙️ Environment Variables

Configure these in `backend/.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key | `""` |
| `ANTHROPIC_API_KEY`| Anthropic Claude API Key | `""` |
| `OPENAI_API_KEY` | OpenAI GPT-4o API Key | `""` |
| `AGENT_MODEL` | Custom model override (e.g. `gemini-3.5-flash`, `gpt-4o-mini`) | Auto |
| `AGENT_TIMEOUT_SECONDS` | Maximum timeout before graceful degradation | `15.0` |
| `DATABASE_PATH` | Path to the SQLite storage file | `./room.db` |
| `MOCK_LLM` | Enable offline mock responder for fast local tests | `false` |

---

## 📁 Project Structure

```
ziroo-shared-agent-room/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application & WebSocket endpoint
│   │   ├── connection_manager.py # WebSocket room pool & JSON broadcasting
│   │   ├── room.py               # Per-user memory threads & asyncio.Lock serialization
│   │   ├── db.py                 # SQLite persistence schema (aiosqlite)
│   │   ├── models.py             # Pydantic data schemas
│   │   └── agent.py              # Multi-provider LLM caller with timeout & error handling
│   ├── tests/                    # Pytest test suite & multi-process live verification
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.svelte            # Root view switcher
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── JoinScreen.svelte      # Name & room entry with random generator
│   │   │   │   ├── ChatRoom.svelte        # Live chat stream & input dock
│   │   │   │   ├── MessageBubble.svelte   # Monochrome DM bubbles & markdown rendering
│   │   │   │   └── TypingIndicator.svelte # Pulsing agent status indicator
│   │   │   ├── stores/
│   │   │   │   └── room.js                # Svelte stores (messages, activeUsers, status)
│   │   │   ├── ws.js                      # WebSocket client wrapper with auto-reconnect
│   │   │   └── markdown.js                # Safe markdown & code parser
│   │   ├── app.css                        # Instagram monochrome dark mode styles
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── AGENTS.md                     # Project specification & locked-in architecture rules
├── NOTES.md                      # Engineering decisions, tradeoffs & evaluation notes
└── README.md
```

---

## 👨‍💻 Author & Connect

Crafted by **Bharath** for the Ziroo Full-Stack Intern Build Assignment.

- 🌐 **Portfolio**: [https://bharath.is-cool.dev/](https://bharath.is-cool.dev/)
- 📄 **Resume**: [https://kuruk.am/bharathresume](https://kuruk.am/bharathresume)
- 🐙 **GitHub**: [@Abez-B](https://github.com/Abez-B)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
