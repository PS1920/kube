import asyncio
from kubernetes_asyncio import client, config, watch
from .manager import manager
from .state_engine import state_engine

async def cluster_tick_loop():
    """Timer that ticks every 5s independently of cluster events to evaluate time-decay statuses."""
    while True:
        try:
            changes = state_engine.tick()
            if changes:
                payload = {
                    "type": "DEPLOYMENT_UPDATE",
                    "deployments": state_engine.get_snapshot()
                }
                await manager.broadcast(payload)
                for change in changes:
                    await manager.broadcast({
                        "type": "SYSTEM_EVENT",
                        "service": change["service"],
                        "status": change["status"]
                    })
        except Exception as e:
            print(f"⚠️ Tick evaluator tick loop error: {e}")
        await asyncio.sleep(5)

async def watch_cluster():
    """Async generator yielding deployment events dynamically updating state_engine."""
    asyncio.create_task(cluster_tick_loop())
    
    while True:
        try:
            await config.load_kube_config()
        except Exception as e:
            print(f"⚠️ Kubeconfig error: {e}. Retrying in 10s...")
            await asyncio.sleep(10)
            continue

        v1_apps = client.AppsV1Api()
        w = watch.Watch()
        
        print("📡 Monitoring Deployments via State Engine (Async)...")
        try:
            # Seed initial fetch reliably onto engine
            deploy_list = await v1_apps.list_namespaced_deployment(namespace="default")
            state_engine.evaluate_deployments(deploy_list.items)
            state_engine.tick()
            
            payload = {
                "type": "DEPLOYMENT_UPDATE",
                "deployments": state_engine.get_snapshot()
            }
            await manager.broadcast(payload)
            
            # React directly to standard events
            async for event in w.stream(v1_apps.list_namespaced_deployment, namespace="default"):
                deploy_list = await v1_apps.list_namespaced_deployment(namespace="default")
                state_engine.evaluate_deployments(deploy_list.items)
                changes = state_engine.tick()
                
                payload = {
                    "type": "DEPLOYMENT_UPDATE",
                    "deployments": state_engine.get_snapshot()
                }
                await manager.broadcast(payload)
                
                if changes:
                    for change in changes:
                        await manager.broadcast({
                            "type": "SYSTEM_EVENT",
                            "service": change["service"],
                            "status": change["status"]
                        })
                
        except Exception as e:
            print(f"⚠️ Watcher stream error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

def start_k8s_watcher_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(watch_cluster())