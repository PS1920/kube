import asyncio
import websockets
import json
import httpx
import time

async def main():
    uri = "ws://127.0.0.1:8000/ws"
    print("Connecting to WebSocket...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Trigger chaos injection
            print("Triggering Chaos via HTTP...")
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "http://127.0.0.1:8000/api/chaos/start",
                    json={"service": "inventory-service", "fault": "crashloop"}
                )
                print(f"HTTP POST /api/chaos/start returned: {res.status_code} {res.json()}")

            # Wait for and print websocket events
            start = time.time()
            events = []
            while time.time() - start < 5:
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    events.append(message_str)
                    print(f"WS EVENT: {message_str}")
                except asyncio.TimeoutError:
                    continue
            
            print(f"Collected {len(events)} WebSocket messages.")
            
    except Exception as e:
        print(f"WebSocket Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
