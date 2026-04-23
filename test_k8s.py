import asyncio
from kubernetes_asyncio import client, config

async def main():
    await config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = await v1.list_pod_for_all_namespaces()
    print(f"Found {len(pods.items)} pods in K8s")
    for p in pods.items[:5]:
        print("-", p.metadata.name)

asyncio.run(main())
