from fastapi import FastAPI
import time

app = FastAPI()

delay = 0

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/products")
def get_products():
    time.sleep(delay)
    return {"products": ["item1", "item2", "item3"]}

@app.post("/simulate-latency")
def simulate_latency(seconds: int):
    global delay
    delay = seconds
    return {"message": f"Latency set to {seconds} seconds"}