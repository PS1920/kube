from typing import List
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from .engine import inject_failure, get_pod_logs_async, describe_pod_async, create_pod_async
from .graph import graph_db
from .vector import vector_db

@tool
async def delete_pods(pod_names: str, namespace: str = "default") -> str:
    """Deletes/restarts one or more kubernetes pods. Input can be a single pod name or a comma-separated list of pod names."""
    names = [n.strip() for n in pod_names.split(",") if n.strip()]
    results = []
    for pod_name in names:
        result = await inject_failure(pod_name, namespace)
        if result.get("status") == "success":
            results.append(f"Successfully deleted {pod_name}.")
        else:
            results.append(f"Failed to delete {pod_name}: {result.get('message')}")
    
    return "\n".join(results)

@tool
async def get_pod_logs(pod_name: str, namespace: str = "default") -> str:
    """Retrieves the last 50 lines of logs for a specific pod."""
    result = await get_pod_logs_async(pod_name, namespace)
    if result.get("status") == "success":
        return result.get("logs") or "Pod created successfully but contains no logs yet."
    return f"Failed to get logs: {result.get('message')}"

@tool
async def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """Retrieves metadata, assigned node, IPs, and restart count for a specific pod. Use this to view a pod."""
    result = await describe_pod_async(pod_name, namespace)
    if result.get("status") == "success":
        return _truncate(result.get("description"), 800)
    return f"Failed to describe pod: {result.get('message')}"

@tool
async def create_basic_pod(pod_name: str, image: str, namespace: str = "default") -> str:
    """Creates a basic pod in the cluster. Requires the desired name and the container image (e.g., 'nginx')."""
    result = await create_pod_async(pod_name, image, namespace)
    if result.get("status") == "success":
        return result.get("message")
    return f"Failed to create pod: {result.get('message')}"

def _truncate(text: str, limit: int = 1000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n...[TRUNCATED TO SAVE CONTEXT TOKEN LIMITS]"

@tool
async def search_anomalous_logs(query: str) -> str:
    """Searches the vector database for anomalous logs matching a symptom or query."""
    results = await vector_db.search_similar_logs(query)
    if not results:
        return "No similar anomalous logs found."
    
    formatted = "\n".join([f"Pod: {r['pod']}, Log: {r['text']} (score: {r['score']:.2f})" for r in results])
    return _truncate(f"Simliar logs:\n{formatted}", 1000)

@tool
async def check_dependencies() -> str:
    """Checks the current live graph of cluster components to understand upstream/downstream impact."""
    status_data = await graph_db.get_status()
    lines = []
    for link in status_data.get("dependencies", []):
        lines.append(f"{link['from']} --[DEPENDS_ON]--> {link['to']}")
    
    if not lines:
        return "No dependencies mapped."
    return _truncate("\n".join(lines), 500)

@tool
async def list_deployments(namespace: str = "default") -> str:
    """Lists all active deployments and their health state based on running vs desired replicas."""
    from kubernetes_asyncio import client, config
    from backend.state_engine import state_engine
    try:
        await config.load_kube_config()
        v1_apps = client.AppsV1Api()
        deploy_list = await v1_apps.list_namespaced_deployment(namespace=namespace)
        
        state_engine.evaluate_deployments(deploy_list.items)
        state_engine.tick()
        snapshot = state_engine.get_snapshot()
        
        deploys = []
        for d in snapshot:
            deploys.append(f"{d['name']} (State: {d['status']}, {d['running']}/{d['desired']} healthy - Event: {d['event_message']})")
            
        if not deploys:
            return f"No deployments found in namespace {namespace}."
        return _truncate(f"Total deployments across {namespace}: {len(deploys)}. Details: " + ", ".join(deploys), 800)
    except Exception as e:
        return f"Failed to list deployments natively: {str(e)}"

@tool
async def check_root_cause(failing_deployment: str) -> str:
    """Uses the dependency graph to check if a failing deployment is caused by an upstream deployment failure."""
    # Simplified graph dependency cross-reference
    topology = await graph_db.get_topology()
    upstream = []
    for link in topology.get("links", []):
        if link['source'] == failing_deployment:
            upstream.append(link['target'])
    
    if not upstream:
        return f"No documented upstream dependencies for {failing_deployment}. The failure is likely local to this deployment."
    
    return f"{failing_deployment} depends on: {', '.join(upstream)}. Please check the health of these upstream dependencies."

# Initialize the Groq LLM using Llama-3.1-8b (to avoid early token rate limits)
llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0, 
    max_retries=5, 
    timeout=30.0
)

# The tools the agent can use to Reason, Act, and Observe
tools = [delete_pods, search_anomalous_logs, check_dependencies, check_root_cause, list_deployments, get_pod_logs, describe_pod, create_basic_pod]

# Initialize the LangGraph ReAct Agent
agent_executor = create_react_agent(llm, tools)

async def stream_ai_analysis(selected_service: str, nodes: list, dependencies: list):
    """
    Optimized streaming AI analysis bound directly to UI-injected live state matrices.
    """
    # 1. HARD GATE: All healthy check
    all_healthy = all(n.get('status') == 'healthy' for n in nodes)
    
    if all_healthy:
        yield "System is healthy. All services are stable."
        return

    # Extract target node directly from truth payload
    target_node = next((n for n in nodes if n.get('name') == selected_service), None)
    if not target_node:
        yield f"Cannot analyze: {selected_service} is no longer mapped in the topology."
        return

    # 3. Filter dependencies strictly against failed nodes natively mapped in `nodes` array
    failed_nodes = {n.get('name') for n in nodes if n.get('status') in ['failed', 'degraded', 'error']}
    
    deps = []
    for link in dependencies:
        if link['from'] == selected_service:
            if link['to'] in failed_nodes:
                deps.append(f"{link['to']} (DOWN)")
            else:
                deps.append(f"{link['to']} (HEALTHY)")
    
    dependent_on = ", ".join(deps) if deps else "none explicitly mapped"
    other_issues = [name for name in failed_nodes if name != selected_service]
    other_context = f" Other failing services: {', '.join(other_issues)}." if other_issues else ""

    sys_message = (
        "You are an AI Root Cause Explainer parsing real-time Kubernetes dependency topologies. Keep responses short and highly readable. "
        "CRITICAL RULES:\n"
        "1. You MUST explicitly end your response with a Confidence indicator: '(Confidence: HIGH)', '(Confidence: MEDIUM)', or '(Confidence: LOW)'.\n"
        "2. MULTI-FAILURE: If multiple services are failing, explicitly identify and prioritize the root-most service (the service actively failing that has NO upstream failing dependencies itself) as the true root cause.\n"
        "3. PARTIAL GRAPH: If some dependencies exist but map may clearly be missing downstream chains to fully explain it, you MUST reply: 'Based on available data, [Service] is likely the cause, but dependency mapping may be incomplete. (Confidence: MEDIUM)'\n"
        "4. FALLBACK SAFETY: If the provided data prevents you from forming any confident logical chain, you MUST return EXACTLY: 'Unable to determine exact root cause. Multiple factors may be involved. (Confidence: LOW)'\n"
        "5. EXACT FORMAT: If confident, strictly use: '[IMPACT] because [ROOT CAUSE].'\n"
        f"Context: Target Service '{selected_service}' status is '{target_node.get('status')}'.\n"
        f"Dependencies explicitly mapped to {selected_service}: {dependent_on}.\n"
        f"{other_context}"
    )
    
    # Generate and yield dynamically
    async for chunk in llm.astream([
        ("system", sys_message),
        ("user", "Explain why this service is failing based on the context provided.")
    ]):
        if chunk.content:
            yield chunk.content

async def trigger_agent(anomaly_description: str):
    """
    Triggers the AI agent to investigate an anomaly and act.
    Returns the agent's thought process and actions.
    """
    sys_message = (
        "You are 'Kubee', a human-sounding DevOps engineer and Kubernetes Reliability expert. "
        "Explain system status to your teammate using simple, conversational language. "
        "CRITICAL INSTRUCTION: You may ONLY use the tools explicitly provided to you. Use `list_deployments` to check status. Use `check_root_cause` for dependencies. "
        "Rules:\n"
        "- Avoid robotic phrases like 'partial availability detected' or 'failure detected'.\n"
        "- Explain what is happening AND why.\n"
        "- Keep it short and clear (2-3 sentences max).\n"
        "- Examples of good tone:\n"
        "  Instead of 'Service degraded': 'Looks like one of the replicas is missing right now, so the service isn’t fully stable. Kubernetes is trying to bring it back up.'\n"
        "  Instead of 'Pod deleted': 'A pod was replaced, which is normal—Kubernetes is handling it automatically.'\n"
    )
    
    inputs = {
        "messages": [
            ("system", sys_message),
            ("user", f"Anomaly detected: {anomaly_description}\nPlease investigate and take remediation actions.")
        ]
    }
    
    result = await agent_executor.ainvoke(inputs)
    
    # Return the final message content
    return result["messages"][-1].content

async def chat_with_agent(user_message: str, history: list = None):
    """
    General conversational endpoint for the AI assistant with short-term memory.
    """
    sys_message = (
        "You are 'Kubee', a human-sounding DevOps engineer and Kubernetes Reliability expert assisting your teammate. "
        "You ONLY have access to these exact tools: list_deployments, check_root_cause, check_dependencies, search_anomalous_logs, delete_pods, get_pod_logs, describe_pod, create_basic_pod. "
        "Rules:\n"
        "- Explain what is happening AND why using simple, conversational language.\n"
        "- Keep it short and clear (2-3 sentences max).\n"
        "- Avoid robotic phrases. Instead of 'Service degraded', say 'Looks like one of the replicas is missing right now, so the service isn’t fully stable.'\n"
        "- If the user asks to arbitrarily delete components, ask clarifying questions before triggering deletion."
    )
    
    messages = [("system", sys_message)]
    
    if history:
        for msg in history:
            role = "assistant" if msg.get("sender") == "bot" else "user"
            messages.append((role, msg.get("text", "")))
            
    messages.append(("user", user_message))
    
    inputs = {"messages": messages}
    
    result = await agent_executor.ainvoke(inputs)
    return result["messages"][-1].content
