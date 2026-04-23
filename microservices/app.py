import os
import random
import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()
SERVICE_NAME = os.environ.get("SERVICE_NAME", "unknown-service")

@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

# ==========================================
# 1. USER SERVICE
# ==========================================
@app.get("/validate")
def validate_user():
    if SERVICE_NAME != "user-service":
        raise HTTPException(status_code=404)
    # Simulate occasional token failures
    if random.random() < 0.05:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user_id": "u_123", "valid": True}

# ==========================================
# 2. PRODUCT SERVICE
# ==========================================
@app.get("/product")
def get_product():
    if SERVICE_NAME != "product-service":
        raise HTTPException(status_code=404)
    return {"product_id": "p_99", "price": 49.99, "name": "Neural Link Pro"}

# ==========================================
# 3. INVENTORY SERVICE
# ==========================================
@app.get("/inventory")
def check_inventory():
    if SERVICE_NAME != "inventory-service":
        raise HTTPException(status_code=404)
    stock = random.randint(0, 100)
    if stock == 0:
        raise HTTPException(status_code=400, detail="Out of stock")
    return {"stock": stock}

# ==========================================
# 4. SHIPPING SERVICE
# ==========================================
@app.post("/ship")
def ship_order():
    if SERVICE_NAME != "shipping-service":
        raise HTTPException(status_code=404)
    return {"tracking_num": "TRK_777888999", "status": "Shipped"}

# ==========================================
# 5. PAYMENT SERVICE (ORCHESTRATOR)
# ==========================================
@app.post("/pay")
async def process_payment():
    if SERVICE_NAME != "payment-service":
        raise HTTPException(status_code=404)
    
    # In K8s, services communicate via their Service name DNS
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # 1. Validate User
            user_res = await client.get("http://user-service:8000/validate")
            if user_res.status_code != 200:
                raise HTTPException(status_code=402, detail="Payment Failed: User validation failed")
            
            # 2. Fetch Product (Delay/Failure sensitive)
            prod_res = await client.get("http://product-service:8000/product")
            if prod_res.status_code != 200:
                raise HTTPException(status_code=402, detail="Payment Failed: Product catalog unavailable")
            
            # 3. Check Inventory (Can be out of stock or dead)
            inv_res = await client.get("http://inventory-service:8000/inventory")
            if inv_res.status_code != 200:
                raise HTTPException(status_code=402, detail="Payment Failed: Inventory unavailable or empty")
            
            # 4. Simulate payment processing logic (20% random failure on valid flows)
            if random.random() < 0.20:
                raise HTTPException(status_code=500, detail="Payment Declined by Gateway")
            
            # 5. Trigger Shipping
            ship_res = await client.post("http://shipping-service:8000/ship")
            shipping_status = "Success" if ship_res.status_code == 200 else "Partial Success - Shipping Delayed"

            return {"transaction_id": "TX_999", "status": "Payment Complete", "shipping": shipping_status}

    except httpx.RequestError as exc:
        # A DNS or timeout error to an internal service
        raise HTTPException(status_code=503, detail=f"Payment Failed due to internal dependency error: {exc.request.url}")
