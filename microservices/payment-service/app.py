from fastapi import FastAPI, HTTPException

app = FastAPI()

fail = False

@app.get("/health")
def health():
    return {"status": "ok" if not fail else "error"}

@app.post("/pay")
def pay():
    if fail:
        raise HTTPException(status_code=500, detail="Payment failed")
    return {"message": "Payment successful"}

@app.post("/simulate-failure")
def simulate_failure(state: bool):
    global fail
    fail = state
    return {"failure_mode": fail}