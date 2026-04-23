import asyncio
import time
import random
from kubernetes_asyncio import client, config
from .manager import manager
from .engine import inject_failure

class ChaosExperiment:
    def __init__(self):
        self.active_experiments = {}

    async def _safe_broadcast(self, payload):
        print(f"DEBUG: Before broadcast - TYPE: {payload.get('type')}")
        try:
            await manager.broadcast(payload)
            print(f"DEBUG: After broadcast - TYPE: {payload.get('type')} successful")
        except Exception as e:
            print(f"[CRITICAL ERROR] WebSocket broadcast failed: {e}")

    async def start_targeted_fault(self, service_name: str, fault_type: str, namespace="default"):
        print("CHAOS FUNCTION ENTERED")
        try:
            experiment_id = f"chaos-{service_name}-{int(time.time())}"
            self.active_experiments[experiment_id] = {
                "target": service_name,
                "start_time": time.time(),
                "status": "INJECTED",
                "tracker_state": "failed" # to track state machine enforcement
            }
            
            await self._safe_broadcast({
                "type": "CHAOS_LOG",
                "message": f"Injecting {fault_type} into {service_name}..."
            })
            
            await self._safe_broadcast({
                "type": "SYSTEM_EVENT",
                "service": service_name,
                "status": "failed"
            })

            try:
                print("DEBUG: Before K8s connection config load...")
                await config.load_kube_config()
                print("DEBUG: After K8s connection config load (success).")
            except Exception as e:
                print(f"[CRITICAL ERROR] K8s connection failed: {e}")
                raise Exception("Cluster unreachable")

            print("DEBUG: Before K8s read_namespaced_deployment...")
            v1_apps = client.AppsV1Api()
            
            # 1. Grab original deployment to remember replicas
            orig_dep = await v1_apps.read_namespaced_deployment(name=service_name, namespace=namespace)
            orig_replicas = orig_dep.spec.replicas or 1
            print(f"DEBUG: After K8s read_namespaced_deployment (success), orig_replicas: {orig_replicas}")
            
            await self._safe_broadcast({
                "type": "CHAOS_LOG",
                "message": "Pod terminated..."
            })
            
            body = {
                "spec": {
                    "replicas": 0
                }
            }
            print("DEBUG: Before K8s patch_namespaced_deployment to 0 replicas...")
            await v1_apps.patch_namespaced_deployment(name=service_name, namespace=namespace, body=body)
            print("DEBUG: After K8s patch_namespaced_deployment (success).")

            # Wait briefly and verify impact
            await asyncio.sleep(2)
            check_dep = await v1_apps.read_namespaced_deployment(name=service_name, namespace=namespace)
            if check_dep.status.ready_replicas is not None and check_dep.status.ready_replicas >= orig_replicas:
                print("[CRITICAL ERROR] Chaos injection ineffective: ready_replicas not reduced")
                await self._safe_broadcast({
                    "type": "CHAOS_LOG",
                    "message": "Chaos injection ineffective!"
                })

            # Monitor and heal
            asyncio.create_task(self._simulate_and_heal(experiment_id, service_name, namespace, orig_replicas))
            
            return {"status": "success", "experiment_id": experiment_id}
            
        except Exception as e:
            print(f"[CRITICAL ERROR] Chaos function failed: {e}")
            await self._safe_broadcast({
                "type": "SYSTEM_EVENT",
                "service": service_name,
                "status": "failed"
            })
            await self._safe_broadcast({
                "type": "CHAOS_LOG",
                "message": f"Experiment failed to execute: {e}"
            })
            return {"error": str(e)}

    async def _simulate_and_heal(self, experiment_id, service_name, namespace, orig_replicas):
        try:
            await asyncio.sleep(15) # Wait 15s to let the system stay in "failed" state
            
            await self._safe_broadcast({
                "type": "CHAOS_LOG",
                "message": f"Recovering {service_name}..."
            })
            
            v1_apps = client.AppsV1Api()
            try:
                # Restore replicas
                body = {
                    "spec": {
                        "replicas": orig_replicas
                    }
                }
                await v1_apps.patch_namespaced_deployment(name=service_name, namespace=namespace, body=body)
            except Exception as e:
                print(f"[CRITICAL ERROR] K8s recovery patch failed: {e}")
                
            # Monitor for actual recovery
            start_time = self.active_experiments[experiment_id]["start_time"]
            recovered = False
            last_state = "failed"
            
            while not recovered:
                await asyncio.sleep(2)
                try:
                    dep = await v1_apps.read_namespaced_deployment(name=service_name, namespace=namespace)
                    ready = dep.status.ready_replicas or 0
                    
                    print(f"LOOP RUNNING | READY: {ready} | ORIG_DESIRED: {orig_replicas}")
                    
                    new_state = "failed"
                    if ready == 0:
                        new_state = "failed"
                    elif 0 < ready < orig_replicas:
                        new_state = "recovering"
                    elif ready >= orig_replicas:
                        new_state = "healthy"
                        
                    # State machine skip warning
                    if new_state == "healthy" and last_state == "failed":
                        print(f"[WARNING] State machine skipped RECOVERING state for {service_name}")
                        
                    last_state = new_state
                    
                    if new_state == "failed":
                        await self._safe_broadcast({
                            "type": "SYSTEM_EVENT",
                            "service": service_name,
                            "status": "failed"
                        })
                    elif new_state == "recovering":
                        await self._safe_broadcast({
                            "type": "SYSTEM_EVENT",
                            "service": service_name,
                            "status": "recovering"
                        })
                    elif new_state == "healthy":
                        delta = time.time() - start_time
                        await self._safe_broadcast({
                            "type": "SYSTEM_EVENT",
                            "service": service_name,
                            "status": "healthy"
                        })
                        await self._safe_broadcast({
                            "type": "CHAOS_LOG",
                            "message": f"Recovery complete | MTTR: {delta:.2f} sec"
                        })
                        recovered = True
                except Exception as e:
                    print(f"[CRITICAL ERROR] Exception inside recovery polling logic: {e}")
        except Exception as e:
            print(f"[CRITICAL ERROR] Simulate and heal failed: {e}")

chaos_engine = ChaosExperiment()
