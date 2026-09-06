import pytest
import asyncio
import os
import json
import websockets
import uvicorn
from multiprocessing import Process
import time

def run_server():
    os.environ["MOCK_LLM"] = "true"
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8032, log_level="warning")

@pytest.mark.asyncio
async def test_context_isolation_between_two_users():
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(1.2)

    try:
        room_code = f"context-iso-{int(time.time()*1000)}"
        uri_a = f"ws://127.0.0.1:8032/ws/{room_code}?name=Alice"
        uri_b = f"ws://127.0.0.1:8032/ws/{room_code}?name=Bob"

        async with websockets.connect(uri_a) as ws_a, websockets.connect(uri_b) as ws_b:
            events_a = []
            events_b = []

            async def listen(ws, container):
                try:
                    while True:
                        msg = await ws.recv()
                        container.append(json.loads(msg))
                except Exception:
                    pass

            task_a = asyncio.create_task(listen(ws_a, events_a))
            task_b = asyncio.create_task(listen(ws_b, events_b))

            await asyncio.sleep(0.3)

            # Step 1: Alice tells agent her secret color
            await ws_a.send(json.dumps({"content": "@agent My favorite color is emerald green."}))
            await asyncio.sleep(0.4)

            # Step 2: Bob asks agent for his favorite color
            await ws_b.send(json.dumps({"content": "@agent What is my favorite color?"}))
            await asyncio.sleep(0.4)

            # Step 3: Alice asks agent for her favorite color
            await ws_a.send(json.dumps({"content": "@agent What was my favorite color?"}))
            await asyncio.sleep(0.4)

            task_a.cancel()
            task_b.cancel()

            # Find agent replies
            agent_msgs = [e["payload"] for e in events_a if e.get("type") == "chat_message" and e["payload"]["role"] == "agent"]
            
            alice_replies = [m for m in agent_msgs if m["target_user"] == "Alice"]
            bob_replies = [m for m in agent_msgs if m["target_user"] == "Bob"]

            assert len(alice_replies) == 2
            assert len(bob_replies) == 1

            assert "emerald green" not in bob_replies[0]["content"].lower()
            assert "don't recall" in bob_replies[0]["content"].lower() or "not" in bob_replies[0]["content"].lower()

            assert "emerald green" in alice_replies[1]["content"].lower()
    finally:
        proc.terminate()
        proc.join()
