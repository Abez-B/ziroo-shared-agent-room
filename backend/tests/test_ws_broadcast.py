import pytest
import asyncio
import json
import websockets
import uvicorn
from multiprocessing import Process
import time

def run_server():
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8031, log_level="warning")

@pytest.mark.asyncio
async def test_websocket_broadcast_between_two_users():
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(1.2)

    try:
        room_code = f"ws-broadcast-{int(time.time()*1000)}"
        uri_a = f"ws://127.0.0.1:8031/ws/{room_code}?name=Alice"
        uri_b = f"ws://127.0.0.1:8031/ws/{room_code}?name=Bob"

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

            # Alice sends a message
            await ws_a.send(json.dumps({"content": "Hello Bob! Are you ready?"}))
            await asyncio.sleep(0.3)

            # Bob sends a message
            await ws_b.send(json.dumps({"content": "Yes Alice, all systems ready."}))
            await asyncio.sleep(0.3)

            task_a.cancel()
            task_b.cancel()

            # Verify both saw Alice's and Bob's messages
            chat_msgs_a = [e["payload"] for e in events_a if e.get("type") == "chat_message"]
            chat_msgs_b = [e["payload"] for e in events_b if e.get("type") == "chat_message"]

            assert any(m["user_name"] == "Alice" and m["content"] == "Hello Bob! Are you ready?" for m in chat_msgs_a)
            assert any(m["user_name"] == "Alice" and m["content"] == "Hello Bob! Are you ready?" for m in chat_msgs_b)

            assert any(m["user_name"] == "Bob" and m["content"] == "Yes Alice, all systems ready." for m in chat_msgs_a)
            assert any(m["user_name"] == "Bob" and m["content"] == "Yes Alice, all systems ready." for m in chat_msgs_b)
    finally:
        proc.terminate()
        proc.join()
