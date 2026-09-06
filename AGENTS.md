# AGENTS.md — Project Rules for AI Coding Agents

This file is read automatically by Antigravity (and other AGENTS.md-aware
tools) on project open. It is the brief for implementing this repo — it
restates the assignment as locked-in decisions so there's no ambiguity
left to resolve mid-build. If you hit a genuine ambiguity not covered
here, make a reasonable call and log it in NOTES.md under "Assumptions" —
don't stall on it, don't ask the user to resolve it, just proceed.

## Project overview
- **Name:** Ziroo Shared Agent Room
- **Type:** Full-stack web app (real-time multiplayer chat room with an AI participant)
- **Stage:** Prototype / take-home assignment (5–6 hour timebox — do not gold-plate)

## Tech stack (locked in, do not deviate without a strong reason)
- **Backend language/framework:** Python, FastAPI
- **Realtime transport:** WebSockets
- **Persistence:** SQLite (stdlib `sqlite3` or `sqlmodel`)
- **Frontend:** Svelte (via SvelteKit or plain Vite + Svelte — either is fine, note which and why in NOTES.md)
- **Package managers:** pip (backend), npm (frontend)

## The core problem (read this twice)

Two users share one room and both can address an AI agent (`@agent ...`)
in the same shared message stream. The agent must keep each user's own
conversation thread straight — User A's question/context must never leak
into the answer given to User B — even though delivery is shared.

**This is the #1 evaluation criterion.** Everything else is scaffolding
around this one problem. If it works for one user and breaks with two,
the submission fails regardless of how polished anything else is.

## Locked-in architecture decisions

### Transport: WebSockets
Both users can type at once and need to see messages arrive live in both
directions — SSE is one-way, polling is wasteful. Use a single WebSocket
endpoint per room, e.g. `ws://.../ws/{room_code}?name={user_name}`.

### Backend: FastAPI (Python)
- `ConnectionManager` — tracks live WebSocket connections keyed by room code.
- `Room` — in-memory representation of a room: ordered message log +
  an `asyncio.Lock` (or single-consumer `asyncio.Queue`) so concurrent
  inbound messages from A and B are processed one at a time in a stable,
  deterministic order instead of racing each other.
- **Context isolation (the core requirement):** the agent is NOT given
  "the room's chat log." It is given that specific user's own message
  history, scoped by `(room_code, user_name)`. Two users in the same room
  produce two independent agent conversation threads. Optionally include
  light shared room context (e.g. "you are in room X with users A and B")
  but never the other user's actual message content or the agent's replies
  to them.
- Persist messages to **SQLite** (stdlib `sqlite3`, or `sqlmodel`/`sqlalchemy`
  if that's faster to write correctly). Minimum schema:
  - `messages(id, room_code, user_name, role, content, created_at)`
    where `role` is `human` | `agent` | `system`.
  - On server restart, reload each room's message log and per-user agent
    thread from this table before accepting new connections.
- Agent call: one call per `@agent`-addressed message. No per-keystroke
  calls, no multi-stage pipelines.
  - Wrap the call in try/except with a timeout (e.g. 15–20s).
  - On failure/timeout/malformed response: emit a visible system message
    in the room (e.g. "⚠️ agent couldn't respond, try again") instead of
    crashing the connection or hanging either client.
  - Broadcast a "typing"/"thinking" indicator scoped to the room while the
    call is in flight, and clear it on completion or failure.

### Frontend: Svelte
Screens/states required:
1. **Join screen** — name + room code, no real auth.
2. **Chat screen**:
   - Message list, ordered, auto-scrolling.
   - Visually distinct styling for: your own messages, the other human's
     messages, agent messages, and system/error messages.
   - Loading/"agent is thinking" indicator while a call is in flight.
   - Empty state for a freshly created room.
3. Two browser tabs (different names, same room code) represent the two
   users — no real auth system needed.

Use Svelte stores for room/connection state (a writable store for the
message list, a derived store for connection status is plenty — no need
for anything heavier). Keep the WebSocket client logic in its own module
so components stay declarative.

### Concurrency
Document (in NOTES.md) what happens when A and B send `@agent` messages
within the same second: they should both get processed and answered
without interleaving or corrupting each other's context. A per-room lock/
queue that processes one inbound message at a time is sufficient — no
need for a distributed or scalable solution.

### AI provider
Any provider/key is fine (Anthropic, OpenAI, Gemini). Model choice isn't
evaluated. Read the key from an environment variable, never hardcode it,
never commit it. Put the required env var name in `.env.example`.

## Suggested file layout

```
backend/
  app/
    main.py            # FastAPI app, WebSocket endpoint
    connection_manager.py
    room.py             # Room state, per-user threads, lock/queue
    db.py                # SQLite setup + read/write helpers
    agent.py             # LLM call wrapper: timeout, retries, failure handling
  requirements.txt
  .env.example
frontend/
  src/
    App.svelte
    lib/
      components/
        JoinScreen.svelte
        ChatRoom.svelte
        MessageBubble.svelte
        TypingIndicator.svelte
      stores/
        room.js           # writable store: messages, connection state
      ws.js                # WebSocket client wrapper
    main.js
  package.json
```

## Build order (roughly matches eval priority)

1. WebSocket room join + broadcast (no agent yet) — prove two tabs can
   see each other's messages live.
2. Per-user message history + `@agent` detection + agent call wired in,
   with **context isolation** as the explicit design goal — test with two
   tabs asking different, unrelated things back to back and confirm no
   cross-talk.
3. Concurrency: fire near-simultaneous `@agent` messages from both tabs,
   confirm both get correct, non-mixed answers.
4. SQLite persistence: restart the server mid-session, confirm room state
   and agent threads survive.
5. Failure handling: simulate a broken/slow API key and confirm the room
   degrades gracefully instead of hanging or crashing.
6. Frontend polish: empty state, typing indicator, message styling.
7. Write README.md (setup) and NOTES.md (what was tested vs. assumed,
   tradeoffs, what you'd improve with more time).

## Explicit non-goals

- No real authentication system.
- No horizontal scalability / multi-server support.
- No evaluation of which LLM or model was chosen.
- No need to optimize token usage beyond "don't call the API per keystroke."

## Code quality
- Keep files focused — split a file if it's doing more than one job
  (e.g. connection management vs. room state vs. agent calls are separate
  modules, per the layout above).
- No secrets in code or commits — env vars only, read via `.env`.
- Prefer clear, boring code over cleverness; this is evaluated on judgment,
  not sophistication.

## Working agreement
- Update `NOTES.md` as you go (assumptions, tradeoffs, what's tested vs.
  not) — don't leave it all for the end.
- Update `README.md`'s "Status" section once the app runs end to end.
- Follow the build order above; don't jump to frontend polish before
  context isolation and concurrency are verified working.
