import asyncio
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

def run_server():
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8008, log_level="warning")

async def main():
    transcript = []
    room_code = "concurrency-live-room"
    uri_a = f"ws://127.0.0.1:8008/ws/{room_code}?name=Alice"
    uri_b = f"ws://127.0.0.1:8008/ws/{room_code}?name=Bob"

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
                        target = p.get("target_user")
                        target_info = f" [to {target}]" if target else ""
                        transcript.append(f"[{name}'s view] <{sender}{target_info}>: {content}")
                    elif event_type == "typing":
                        p = data["payload"]
                        if p.get("is_typing"):
                            transcript.append(f"[{name}'s view] ... (agent is thinking for {p.get('target_user')}) ...")
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        task_a = asyncio.create_task(listen(ws_a, "Alice"))
        task_b = asyncio.create_task(listen(ws_b, "Bob"))

        await asyncio.sleep(0.3)

        transcript.append(">>> FIRING SIMULTANEOUS INGESTION FROM ALICE AND BOB <<<")
        # Concurrent firing
        await asyncio.gather(
            ws_a.send(json.dumps({"content": "@agent My favorite food is Pizza."})),
            ws_b.send(json.dumps({"content": "@agent My favorite food is Sushi."}))
        )

        await asyncio.sleep(0.6)

        transcript.append(">>> FIRING SIMULTANEOUS QUERIES FROM ALICE AND BOB <<<")
        await asyncio.gather(
            ws_a.send(json.dumps({"content": "@agent What is my favorite food?"})),
            ws_b.send(json.dumps({"content": "@agent What is my favorite food?"}))
        )

        await asyncio.sleep(0.8)

        task_a.cancel()
        task_b.cancel()

    print("\n=================================================================")
    print("=== LIVE STEP 3 CONCURRENCY & SERIALIZATION TRANSCRIPT ===")
    print("=================================================================")
    for line in transcript:
        print(line)
    print("=================================================================\n")

if __name__ == "__main__":
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(1.0)
    try:
        asyncio.run(main())
    finally:
        proc.terminate()
