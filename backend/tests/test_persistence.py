import pytest
import asyncio
import os
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

DB_FILE = "/tmp/test_room_persistence.db"

def run_server(port):
    os.environ["MOCK_LLM"] = "true"
    os.environ["DATABASE_PATH"] = DB_FILE
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="warning")

@pytest.mark.asyncio
async def test_sqlite_persistence_and_server_restart():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    room_code = f"persistent-room-{int(time.time()*1000)}"
    port_session_1 = 8011
    port_session_2 = 8012

    # --- SESSION 1: Server running ---
    proc1 = Process(target=run_server, args=(port_session_1,), daemon=True)
    proc1.start()
    time.sleep(1.2)

    try:
        uri_a = f"ws://127.0.0.1:{port_session_1}/ws/{room_code}?name=Alice"
        async with websockets.connect(uri_a) as ws_a:
            await ws_a.send(json.dumps({"content": "@agent Remember this: My secret key is SEC_ALPHA_123"}))
            await asyncio.sleep(0.5)
            while True:
                try:
                    await asyncio.wait_for(ws_a.recv(), timeout=0.2)
                except asyncio.TimeoutError:
                    break
    finally:
        proc1.terminate()
        proc1.join()
        time.sleep(0.5)

    # --- SESSION 2: Brand new server instance booted from same DB ---
    proc2 = Process(target=run_server, args=(port_session_2,), daemon=True)
    proc2.start()
    time.sleep(1.2)

    try:
        uri_a2 = f"ws://127.0.0.1:{port_session_2}/ws/{room_code}?name=Alice"
        uri_b2 = f"ws://127.0.0.1:{port_session_2}/ws/{room_code}?name=Bob"

        async with websockets.connect(uri_a2) as ws_a2, websockets.connect(uri_b2) as ws_b2:
            events_a = []
            events_b = []

            async def listen(ws, container):
                try:
                    while True:
                        msg = await ws.recv()
                        container.append(json.loads(msg))
                except Exception:
                    pass

            task_a = asyncio.create_task(listen(ws_a2, events_a))
            task_b = asyncio.create_task(listen(ws_b2, events_b))

            await asyncio.sleep(0.3)

            sync_events = [e for e in events_a if e.get("type") == "history_sync"]
            assert len(sync_events) > 0
            assert len(sync_events[0]["payload"]["messages"]) >= 2

            # Alice asks agent for her secret key (reconstructed from DB)
            await ws_a2.send(json.dumps({"content": "@agent What is my secret key?"}))
            await asyncio.sleep(0.5)

            # Bob asks for his secret key
            await ws_b2.send(json.dumps({"content": "@agent What is my secret key?"}))
            await asyncio.sleep(0.5)

            task_a.cancel()
            task_b.cancel()

            alice_replies = [e["payload"] for e in events_a if e.get("type") == "chat_message" and e["payload"]["role"] == "agent" and e["payload"]["target_user"] == "Alice"]
            bob_replies = [e["payload"] for e in events_a if e.get("type") == "chat_message" and e["payload"]["role"] == "agent" and e["payload"]["target_user"] == "Bob"]

            assert len(alice_replies) >= 1
            assert "sec_alpha_123" in alice_replies[-1]["content"].lower()

            assert len(bob_replies) >= 1
            assert "sec_alpha_123" not in bob_replies[-1]["content"].lower()
            assert "don't recall" in bob_replies[-1]["content"].lower() or "not" in bob_replies[-1]["content"].lower()

    finally:
        proc2.terminate()
        proc2.join()
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
