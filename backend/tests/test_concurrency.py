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
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8007, log_level="warning")

@pytest.mark.asyncio
async def test_concurrent_agent_calls_serialized():
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(1.2)

    try:
        room_code = f"concurrency-{int(time.time()*1000)}"
        uri_a = f"ws://127.0.0.1:8007/ws/{room_code}?name=Alice"
        uri_b = f"ws://127.0.0.1:8007/ws/{room_code}?name=Bob"

        async with websockets.connect(uri_a) as ws_a, websockets.connect(uri_b) as ws_b:
            await asyncio.sleep(0.2)

            received_a = []
            received_b = []

            async def listen(ws, container):
                try:
                    while True:
                        msg = await ws.recv()
                        container.append(json.loads(msg))
                except Exception:
                    pass

            task_a = asyncio.create_task(listen(ws_a, received_a))
            task_b = asyncio.create_task(listen(ws_b, received_b))

            # Send simultaneous declarations from Alice and Bob
            async def send_msg(ws, content):
                await ws.send(json.dumps({"content": content}))

            await asyncio.gather(
                send_msg(ws_a, "@agent My secret fruit is Mango."),
                send_msg(ws_b, "@agent My secret fruit is Strawberry.")
            )

            await asyncio.sleep(0.5)

            # Fire simultaneous queries
            await asyncio.gather(
                send_msg(ws_a, "@agent What is my secret fruit?"),
                send_msg(ws_b, "@agent What is my secret fruit?")
            )

            await asyncio.sleep(0.5)

            task_a.cancel()
            task_b.cancel()

            agent_msgs_a = [m["payload"] for m in received_a if m.get("type") == "chat_message" and m["payload"]["role"] == "agent"]
            
            alice_replies = [m for m in agent_msgs_a if m["target_user"] == "Alice"]
            bob_replies = [m for m in agent_msgs_a if m["target_user"] == "Bob"]

            assert len(alice_replies) == 2
            assert len(bob_replies) == 2

            assert "mango" in alice_replies[1]["content"].lower()
            assert "strawberry" not in alice_replies[1]["content"].lower()

            assert "strawberry" in bob_replies[1]["content"].lower()
            assert "mango" not in bob_replies[1]["content"].lower()

    finally:
        proc.terminate()
        proc.join()
