import asyncio
import time
import random
from kubernetes_asyncio import client, config
from .manager import manager
from .engine import inject_failure

class ChaosExperiment:
    def __init__(self):
        self.active_experiments = {}

    async def start_targeted_fault(self, service_name: str, fault_type: str, namespace="default"):
        experiment_id = f"chaos-{service_name}-{int(time.time())}"
        self.active_experiments[experiment_id] = {
            "target": service_name,
            "start_time": time.time(),
            "status": "INJECTED"
        }
        
        await manager.broadcast({
            "type": "CHAOS_LOG",
            "message": f"Injecting {fault_type} into {service_name}..."
        })
        
        await manager.broadcast({
            "type": "SYSTEM_EVENT",
            "service": service_name,
            "status": "failed"
        })

        try:
            await config.load_kube_config()
        except Exception:
            pass

        v1 = client.CoreV1Api()
        v1_apps = client.AppsV1Api()
        try:
            # 1. Grab original deployment to remember replicas
            orig_dep = await v1_apps.read_namespaced_deployment(name=service_name, namespace=namespace)
            orig_replicas = orig_dep.spec.replicas or 1
            
            await manager.broadcast({
                "type": "CHAOS_LOG",
                "message": "Pod terminated..."
            })
            
            body = {
                "spec": {
                    "replicas": 0
                }
            }
            await v1_apps.patch_namespaced_deployment(name=service_name, namespace=namespace, body=body)

            # Monitor and heal
            asyncio.create_task(self._simulate_and_heal(experiment_id, service_name, namespace, orig_replicas))
            
            return {"status": "success", "experiment_id": experiment_id}
            
        except Exception as e:
            # Fallback if deployment read fails (e.g., using simpler pods)
            return {"error": str(e)}

    async def _simulate_and_heal(self, experiment_id, service_name, namespace, orig_replicas):
        await asyncio.sleep(15) # Wait 15s to let the system stay in "failed" state
        
        await manager.broadcast({
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
        except Exception:
            pass
            
        # Monitor for actual recovery
        start_time = self.active_experiments[experiment_id]["start_time"]
        recovered = False
        while not recovered:
            await asyncio.sleep(2)
            try:
                dep = await v1_apps.read_namespaced_deployment(name=service_name, namespace=namespace)
                ready = dep.status.ready_replicas or 0
                desired = dep.spec.replicas or 1
                print("LOOP RUNNING")
                print("READY:", ready)
                print("DESIRED:", desired)
                if ready == 0:
                    await manager.broadcast({
                        "type": "SYSTEM_EVENT",
                        "service": service_name,
                        "status": "failed"
                    })
                elif 0 < ready < desired:
                    await manager.broadcast({
                        "type": "SYSTEM_EVENT",
                        "service": service_name,
                        "status": "recovering"
                    })
                elif ready == desired:
                    delta = time.time() - start_time
                    await manager.broadcast({
                        "type": "SYSTEM_EVENT",
                        "service": service_name,
                        "status": "healthy"
                    })
                    await manager.broadcast({
                        "type": "CHAOS_LOG",
                        "message": f"Recovery complete | MTTR: {delta:.2f} sec"
                    })
                    recovered = True
            except Exception as e:
                print(f"Exception inside recovery polling logic: {e}")

chaos_engine = ChaosExperiment()
