from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "backend working"}

@app.get("/api/test")
def test():
    return {"message": "API working"}

# 🔥 ADD THIS (IMPORTANT)
@app.get("/api/deployments")
def get_deployments():
    return [
        {"name": "inventory-service", "status": "healthy", "running": 3, "desired": 3},
        {"name": "payment-service", "status": "degraded", "running": 2, "desired": 3},
        {"name": "auth-service", "status": "healthy", "running": 2, "desired": 2},
        {"name": "notification-service", "status": "failed", "running": 0, "desired": 2}
    ]

# 🔥 ADD THIS ALSO
@app.get("/api/graph/status")
def graph_status():
    return {
        "dependencies": [
            {"from": "inventory-service", "to": "payment-service"},
            {"from": "payment-service", "to": "auth-service"},
            {"from": "auth-service", "to": "notification-service"}
        ]
    }
