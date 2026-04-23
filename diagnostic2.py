import asyncio
import websockets
import json
import httpx
import time
from kubernetes_asyncio import client, config

async def main():
    print("=== BEGIN DIAGNOSTIC SCRIPT ===")
    
    # Init K8s
    await config.load_kube_config()
    v1_apps = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    
    uri = "ws://127.0.0.1:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            
            print("\n[7. KUBERNETES REAL STATE (BEFORE)]")
            pods = await core_v1.list_namespaced_pod("default")
            for p in pods.items:
                print(f"Pod: {p.metadata.name} | Status: {p.status.phase}")
            
            print("\n[1. BACKEND CHAOS LOOP EXECUTION & 2. SYSTEM_EVENT BROADCAST]")
            print("Triggering Chaos on inventory-service...")
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    "http://127.0.0.1:8000/api/chaos/start",
                    json={"service": "inventory-service", "fault": "crashloop"}
                )
            
            print("\n[3. WEBSOCKET RECEIVED EVENTS] & [1. LOOP EXECUTION]")
            start = time.time()
            ws_events = []
            recovering_count = 0
            
            while time.time() - start < 25: # Listen for 25s (Chaos waits 15s to restore)
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg = json.loads(message_str)
                    ws_events.append(msg)
                    
                    if msg.get("type") == "SYSTEM_EVENT":
                        print(f"BROADCAST: {msg}")
                        if msg.get("status") == "recovering":
                            recovering_count += 1
                        
                except asyncio.TimeoutError:
                    continue
            
            print(f"Total WS Events Captured: {len(ws_events)}")
            print(f"Times 'recovering' sent: {recovering_count}")

            print("\n[7. KUBERNETES REAL STATE (AFTER)]")
            pods = await core_v1.list_namespaced_pod("default")
            for p in pods.items:
                print(f"Pod: {p.metadata.name} | Status: {p.status.phase}")
            
            deps = await v1_apps.list_namespaced_deployment("default")
            for d in deps.items:
                if d.metadata.name == "inventory-service":
                    print(f"Deployment: {d.metadata.name} | Ready: {d.status.ready_replicas} | Desired: {d.spec.replicas}")
                    img = d.spec.template.spec.containers[0].image
                    print(f"Current Image: {img}")
                    
    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
