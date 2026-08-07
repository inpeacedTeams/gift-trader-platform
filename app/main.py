from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.core.config import get_settings
from app.routes.arbitrage import router as arbitrage_router
from app.routes.history import router as history_router
from app.routes.markets import router as markets_router
from app.routes.source_status import router as source_status_router

class ServiceStatus(BaseModel):
    service: str
    status: str
    data_mode: str

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET"], allow_headers=["Accept", "Content-Type"])
app.include_router(markets_router, prefix=settings.api_prefix)
app.include_router(arbitrage_router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
app.include_router(source_status_router, prefix=settings.api_prefix)

@app.get("/health", response_model=ServiceStatus)
@app.get("/api/health", response_model=ServiceStatus)
async def health() -> ServiceStatus:
    return ServiceStatus(service=settings.app_name, status="ok", data_mode="live-only")
