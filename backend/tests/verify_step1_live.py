import asyncio
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

def run_server():
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8005, log_level="warning")

async def simulate_user(name: str, room: str, actions: list, transcript: list):
    uri = f"ws://127.0.0.1:8005/ws/{room}?name={name}"
    async with websockets.connect(uri) as ws:
        # Background listener
        async def listener():
            try:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    event_type = data.get("type")
                    if event_type == "chat_message":
                        sender = data["payload"]["user_name"]
                        content = data["payload"]["content"]
                        transcript.append(f"[{name}'s view] <{sender}>: {content}")
                    elif event_type == "system_notice":
                        transcript.append(f"[{name}'s view] [System]: {data['payload']['content']}")
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        task = asyncio.create_task(listener())
        for delay, text in actions:
            await asyncio.sleep(delay)
            transcript.append(f"[{name} SENDS]: {text}")
            await ws.send(json.dumps({"content": text}))

        await asyncio.sleep(0.5)
        task.cancel()

async def main():
    transcript = []
    alice_actions = [
        (0.2, "Hi Bob, welcome to the room!"),
        (0.4, "Can you see my live messages?")
    ]
    bob_actions = [
        (0.3, "Hey Alice! Yes, I see you loud and clear."),
        (0.5, "WebSocket broadcast is working seamlessly!")
    ]

    await asyncio.gather(
        simulate_user("Alice", "test-room", alice_actions, transcript),
        simulate_user("Bob", "test-room", bob_actions, transcript)
    )

    print("=== LIVE STEP 1 WEBSOCKET BROADCAST TRANSCRIPT ===")
    for entry in transcript:
        print(entry)
    print("==================================================")

if __name__ == "__main__":
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(1.0)
    try:
        asyncio.run(main())
    finally:
        proc.terminate()
