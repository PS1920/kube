from fastapi import FastAPI
import time

app = FastAPI()

delay = 0

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ship")
def ship():
    time.sleep(delay)
    return {
        "status": "shipped",
        "delay_applied": delay
    }

@app.post("/simulate-delay")
def simulate_delay(seconds: int):
    global delay
    delay = seconds
    return {"message": f"Shipping delay set to {seconds}s"}