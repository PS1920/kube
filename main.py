import asyncio
import uvicorn
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from backend.manager import manager
from backend.watcher import watch_cluster
from backend.engine import inject_failure

from fastapi.middleware.cors import CORSMiddleware

from backend.graph import graph_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the dependency graph for AI Context logic
    await graph_db.initialize_ecommerce_topology()
    
    # Start the K8s Watcher asynchronously
    task = asyncio.create_task(watch_cluster())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any incoming messages (keep-alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/inject")
async def control_inject(pod_name: str, namespace: str = "default"):
    result = await inject_failure(pod_name, namespace)
    # Echo the command back to the UI terminal via WebSockets
    await manager.broadcast({
        "type": "LOG_SYSTEM",
        "message": f"EXECUTED: {result.get('command', 'ERROR')}"
    })
    return result

from backend.graph import graph_db
from backend.agent import trigger_agent
from backend.chaos import chaos_engine
from pydantic import BaseModel

class AnomalyEvent(BaseModel):
    description: str

class ChaosPayload(BaseModel):
    service: str
    fault: str

from fastapi import BackgroundTasks

@app.post("/api/chaos/start")
async def start_chaos_experiment(payload: ChaosPayload, background_tasks: BackgroundTasks, namespace: str = "default"):
    """Manually triggers a chaos experiment in the background."""
    print("CHAOS STARTED")
    background_tasks.add_task(chaos_engine.start_targeted_fault, payload.service, payload.fault, namespace)
    return {"status": "started"}

@app.post("/api/agent/trigger")
async def trigger_agent_endpoint(event: AnomalyEvent):
    try:
        response = await trigger_agent(event.description)
        # Broadcast the agent action to the UI
        await manager.broadcast({
            "type": "LOG_SYSTEM",
            "message": f"🤖 AI AGENT: {response}"
        })
        return {"status": "success", "agent_response": response}
    except Exception as e:
        return {"error": str(e)}

class ChatMessage(BaseModel):
    message: str
    history: list = []

@app.post("/api/agent/chat")
async def chat_endpoint(payload: ChatMessage):
    from backend.agent import chat_with_agent
    try:
        response = await chat_with_agent(payload.message, payload.history)
        return {"status": "success", "agent_response": response}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/graph/status")
async def get_graph_status():
    try:
        return await graph_db.get_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/topology")
async def get_topology():
    try:
        data = await graph_db.get_topology()
        return data
    except Exception as e:
        return {"error": str(e)}

from kubernetes_asyncio import client, config
from backend.state_engine import state_engine

@app.get("/api/pods")
async def get_pods_legacy():
    # Silently handle unrefreshed React UI polling instances
    try:
        await config.load_kube_config()
        v1 = client.CoreV1Api()
        pod_list = await v1.list_namespaced_pod(namespace="default")
        pods = []
        for pod in pod_list.items:
            pods.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "namespace": pod.metadata.namespace
            })
        return pods
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/deployments")
async def get_deployments():
    try:
        await config.load_kube_config()
        v1_apps = client.AppsV1Api()
        deploy_list = await v1_apps.list_namespaced_deployment(namespace="default")
        
        # Native update forces an immediate accurate snapshot evaluation bypassing tick lag
        state_engine.evaluate_deployments(deploy_list.items)
        state_engine.tick()
        
        return state_engine.get_snapshot()
    except Exception as e:
        print(f"Error fetching deployments from K8s: {e}")
        return {"error": str(e)}

class AiAnalysisPayload(BaseModel):
    selected_service: str
    nodes: list
    dependencies: list

@app.post("/api/ai/analyze")
async def analyze_deployment(payload: AiAnalysisPayload):
    print("AI ANALYSIS CALLED VIA INJECTED STATE")
    from backend.agent import stream_ai_analysis
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        try:
            async for chunk in stream_ai_analysis(payload.selected_service, payload.nodes, payload.dependencies):
                yield chunk
        except Exception as e:
            yield f"Error: {str(e)}"
            
    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/api/ask-ai")
async def ask_ai_endpoint(pod_name: str):
    from backend.agent import chat_with_agent
    try:
        query = f"Assess the status of the deployment roughly named '{pod_name}'. Is it healthy, recovering, degraded, or in failure? Determine its state according to our 4-tier system based strictly on list_deployments output."
        response = await chat_with_agent(query)
        
        return {
            "answer": response,
            "suggestion": "Monitor UI Logs"
        }
    except Exception as e:
        return {"answer": f"Agent error: {str(e)}", "suggestion": "-"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)