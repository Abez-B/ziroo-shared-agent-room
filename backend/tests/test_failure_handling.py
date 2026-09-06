import pytest
import asyncio
import os
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

def run_server(port, force_fail=None):
    if force_fail:
        os.environ["AGENT_FORCE_FAILURE"] = force_fail
    else:
        os.environ.pop("AGENT_FORCE_FAILURE", None)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="warning")

@pytest.mark.asyncio
async def test_agent_timeout_degrades_gracefully():
    port = 8021
    proc = Process(target=run_server, args=(port, "timeout"), daemon=True)
    proc.start()
    time.sleep(1.2)

    try:
        uri_a = f"ws://127.0.0.1:{port}/ws/failure-room?name=Alice"
        uri_b = f"ws://127.0.0.1:{port}/ws/failure-room?name=Bob"

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

            # Alice triggers an @agent call that will timeout
            await ws_a.send(json.dumps({"content": "@agent Explain quantum computing"}))
            await asyncio.sleep(0.5)

            # Verify Alice and Bob saw:
            # 1. Typing start
            # 2. System error message in the chat
            # 3. Typing stop
            typing_events = [e for e in events_a if e.get("type") == "typing"]
            assert any(t["payload"]["is_typing"] is True for t in typing_events)
            assert any(t["payload"]["is_typing"] is False for t in typing_events)

            error_msgs = [
                e["payload"] for e in events_a 
                if e.get("type") == "chat_message" and e["payload"]["role"] == "system"
            ]
            assert len(error_msgs) >= 1
            assert "⚠️" in error_msgs[0]["content"]
            assert "timed out" in error_msgs[0]["content"].lower()

            # Verify socket connections are still 100% alive and responsive!
            await ws_b.send(json.dumps({"content": "Still here and working fine!"}))
            await asyncio.sleep(0.3)

            human_msgs = [
                e["payload"] for e in events_a 
                if e.get("type") == "chat_message" and e["payload"]["role"] == "human" and e["payload"]["user_name"] == "Bob"
            ]
            assert len(human_msgs) >= 1
            assert human_msgs[0]["content"] == "Still here and working fine!"

            task_a.cancel()
            task_b.cancel()
    finally:
        proc.terminate()
        proc.join()

@pytest.mark.asyncio
async def test_agent_upstream_error_degrades_gracefully():
    port = 8022
    proc = Process(target=run_server, args=(port, "error"), daemon=True)
    proc.start()
    time.sleep(1.2)

    try:
        uri = f"ws://127.0.0.1:{port}/ws/error-room?name=Charlie"
        async with websockets.connect(uri) as ws:
            events = []
            async def listen():
                try:
                    while True:
                        msg = await ws.recv()
                        events.append(json.loads(msg))
                except Exception:
                    pass

            task = asyncio.create_task(listen())
            await asyncio.sleep(0.3)

            # Charlie sends @agent query that causes upstream failure
            await ws.send(json.dumps({"content": "@agent Do something"}))
            await asyncio.sleep(0.4)

            error_msgs = [
                e["payload"] for e in events 
                if e.get("type") == "chat_message" and e["payload"]["role"] == "system"
            ]
            assert len(error_msgs) >= 1
            assert "⚠️" in error_msgs[0]["content"]
            assert "503" in error_msgs[0]["content"]

            task.cancel()
    finally:
        proc.terminate()
        proc.join()
