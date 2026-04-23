from kubernetes_asyncio import client, config

async def _get_api():
    try:
        await config.load_kube_config()
    except Exception:
        pass # Handle in-cluster config or default contexts gracefully
    return client.CoreV1Api()

async def inject_failure(pod_name: str, namespace: str = "default"):
    """Deletes a pod to simulate failure/restart."""
    try:
        v1 = await _get_api()
        await v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return {"status": "success", "command": f"kubectl delete pod {pod_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def get_pod_logs_async(pod_name: str, namespace: str = "default", tail_lines: int = 50):
    """Retrieves the recent runtime logs for a pod."""
    try:
        v1 = await _get_api()
        logs = await v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail_lines)
        return {"status": "success", "logs": logs}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def describe_pod_async(pod_name: str, namespace: str = "default"):
    """Returns metadata and detailed spec information about a pod."""
    try:
        v1 = await _get_api()
        pod = await v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        description = f"Node: {pod.spec.node_name}\nIP: {pod.status.pod_ip}\nPhase: {pod.status.phase}\n"
        for i, container in enumerate(pod.status.container_statuses or []):
            description += f"Container {i} ({container.name}) Ready: {container.ready}, Restart Count: {container.restart_count}\n"
        return {"status": "success", "description": description}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def create_pod_async(pod_name: str, image: str, namespace: str = "default"):
    """Creates a basic pod running the specified image."""
    try:
        v1 = await _get_api()
        pod_manifest = client.V1Pod(
            metadata=client.V1ObjectMeta(name=pod_name, labels={"app": pod_name, "Pod": "true"}),
            spec=client.V1PodSpec(
                containers=[client.V1Container(name=pod_name, image=image)]
            )
        )
        await v1.create_namespaced_pod(namespace=namespace, body=pod_manifest)
        return {"status": "success", "message": f"Successfully created pod {pod_name} using image {image}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}