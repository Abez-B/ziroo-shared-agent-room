import asyncio
import os
import json
import uvicorn
import websockets
from multiprocessing import Process
import time

DB_FILE = "/tmp/verify_step4_room.db"

def run_server(port):
    os.environ["DATABASE_PATH"] = DB_FILE
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="warning")

async def session_1():
    print("[1] Session 1 starting... Alice joins and chats.")
    uri = "ws://127.0.0.1:8015/ws/recovery-room?name=Alice"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"content": "@agent Remember this: My persistent token is TOKEN_XYZ_777."}))
        await asyncio.sleep(0.5)
        # Alice verifies immediate response
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "chat_message" and data["payload"]["role"] == "agent":
                print(f"[Session 1] <Agent to Alice>: {data['payload']['content']}")
                break

async def session_2():
    print("[3] Session 2 starting after server restart... Connecting Alice and Bob.")
    uri_a = "ws://127.0.0.1:8016/ws/recovery-room?name=Alice"
    uri_b = "ws://127.0.0.1:8016/ws/recovery-room?name=Bob"
    
    async with websockets.connect(uri_a) as ws_a, websockets.connect(uri_b) as ws_b:
        # Check history sync received by Alice
        sync = json.loads(await ws_a.recv())
        print(f"[Session 2] Alice received replayed history with {len(sync['payload']['messages'])} persisted messages.")

        # Alice asks for her token
        await ws_a.send(json.dumps({"content": "@agent What is my persistent token?"}))
        while True:
            raw = await ws_a.recv()
            data = json.loads(raw)
            if data.get("type") == "chat_message" and data["payload"]["role"] == "agent" and data["payload"]["target_user"] == "Alice":
                print(f"[Session 2] <Agent to Alice>: {data['payload']['content']}")
                break

        # Bob asks for his token
        await ws_b.send(json.dumps({"content": "@agent What is my persistent token?"}))
        while True:
            raw = await ws_b.recv()
            data = json.loads(raw)
            if data.get("type") == "chat_message" and data["payload"]["role"] == "agent" and data["payload"]["target_user"] == "Bob":
                print(f"[Session 2] <Agent to Bob>: {data['payload']['content']}")
                break

def main():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    # 1. Start Server 1
    p1 = Process(target=run_server, args=(8015,), daemon=True)
    p1.start()
    time.sleep(1.2)
    try:
        asyncio.run(session_1())
    finally:
        print("[2] Terminating Server 1 (simulating crash / shutdown)...")
        p1.terminate()
        p1.join()
        time.sleep(1.0)

    # 2. Start Server 2 from same SQLite file
    print("[2] Booting brand new Server 2 from persisted SQLite database...")
    p2 = Process(target=run_server, args=(8016,), daemon=True)
    p2.start()
    time.sleep(1.2)
    try:
        asyncio.run(session_2())
    finally:
        p2.terminate()
        p2.join()
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)

if __name__ == "__main__":
    main()
