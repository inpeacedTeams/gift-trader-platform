from fastapi import FastAPI
from pydantic import BaseModel
from app.routes.arbitrage import router as arbitrage_router
from app.routes.markets import router as markets_router

class ServiceStatus(BaseModel):
    service: str
    status: str
    data_mode: str

app = FastAPI(title="Gift Trader API", version="0.1.0")
app.include_router(markets_router, prefix="/api")
app.include_router(arbitrage_router, prefix="/api")

@app.get("/health", response_model=ServiceStatus)
async def health() -> ServiceStatus:
    return ServiceStatus(service="gift-trader-api", status="ok", data_mode="live-only")
