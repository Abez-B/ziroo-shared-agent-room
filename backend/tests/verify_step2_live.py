import asyncio
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

def run_server():
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8006, log_level="warning")

async def simulate_client(name: str, room: str, script: list, transcript: list):
    uri = f"ws://127.0.0.1:8006/ws/{room}?name={name}"
    async with websockets.connect(uri) as ws:
        async def listen():
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
                            transcript.append(f"[{name}'s view] ... ({p.get('user_name')} is thinking for {p.get('target_user')}) ...")
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        listen_task = asyncio.create_task(listen())

        for delay, message in script:
            await asyncio.sleep(delay)
            transcript.append(f"[{name} ACTION] -> Sends: '{message}'")
            await ws.send(json.dumps({"content": message}))

        await asyncio.sleep(0.8)
        listen_task.cancel()

async def main():
    transcript = []
    
    # Alice and Bob actions interleaved in the shared room
    alice_script = [
        (0.2, "@agent Remember this: My secret project name is Project Odyssey."),
        (0.8, "@agent What is my secret project name?")
    ]
    bob_script = [
        (0.5, "@agent What is my secret project name?"),
        (1.1, "@agent My secret project name is Project Apollo."),
        (1.4, "@agent What is my secret project name?")
    ]

    await asyncio.gather(
        simulate_client("Alice", "shared-strategy-room", alice_script, transcript),
        simulate_client("Bob", "shared-strategy-room", bob_script, transcript)
    )

    print("\n=================================================================")
    print("=== LIVE STEP 2 CONTEXT ISOLATION TRANSCRIPT (TWO CLIENTS) ===")
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
