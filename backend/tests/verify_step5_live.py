import asyncio
import os
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

def run_server(port, fail_mode):
    os.environ["AGENT_FORCE_FAILURE"] = fail_mode
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="warning")

async def test_live_failure(port, test_name):
    transcript = []
    uri_a = f"ws://127.0.0.1:{port}/ws/live-fail?name=Alice"
    uri_b = f"ws://127.0.0.1:{port}/ws/live-fail?name=Bob"

    async with websockets.connect(uri_a) as ws_a, websockets.connect(uri_b) as ws_b:
        async def listen(ws, name):
            try:
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    event_type = data.get("type")
                    if event_type == "chat_message":
                        p = data["payload"]
                        sender = p["user_name"]
                        role = p["role"]
                        content = p["content"]
                        transcript.append(f"[{name}'s view] <{role.upper()} - {sender}>: {content}")
                    elif event_type == "typing":
                        p = data["payload"]
                        state = "thinking..." if p.get("is_typing") else "idle/cleared"
                        transcript.append(f"[{name}'s view] [Typing State]: {p.get('user_name')} is {state} for {p.get('target_user')}")
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        t_a = asyncio.create_task(listen(ws_a, "Alice"))
        t_b = asyncio.create_task(listen(ws_b, "Bob"))

        await asyncio.sleep(0.3)
        transcript.append(">>> Alice sends @agent command during simulated failure <<<")
        await ws_a.send(json.dumps({"content": "@agent Calculate Fibonacci sequence."}))
        
        await asyncio.sleep(0.6)
        transcript.append(">>> Bob sends normal chat right after failure to verify connection health <<<")
        await ws_b.send(json.dumps({"content": "Hey Alice, looks like the agent is resting, but we are still chatting!"}))

        await asyncio.sleep(0.5)
        t_a.cancel()
        t_b.cancel()

    print(f"\n=== LIVE SIMULATION: {test_name} ===")
    for line in transcript:
        print(line)
    print("=====================================================\n")

def main():
    # Test 1: Timeout simulation
    p1 = Process(target=run_server, args=(8025, "timeout"), daemon=True)
    p1.start()
    time.sleep(1.2)
    try:
        asyncio.run(test_live_failure(8025, "TIMEOUT DEGRADATION"))
    finally:
        p1.terminate()
        p1.join()

    # Test 2: Upstream 503 Provider failure simulation
    p2 = Process(target=run_server, args=(8026, "error"), daemon=True)
    p2.start()
    time.sleep(1.2)
    try:
        asyncio.run(test_live_failure(8026, "UPSTREAM 503 ERROR DEGRADATION"))
    finally:
        p2.terminate()
        p2.join()

if __name__ == "__main__":
    main()
