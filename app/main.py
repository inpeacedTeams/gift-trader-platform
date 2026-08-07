from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.core.config import get_settings
from app.routes.analytics import router as analytics_router
from app.routes.arbitrage import router as arbitrage_router
from app.routes.auth import router as auth_router
from app.routes.gifts import router as gifts_router
from app.routes.history import router as history_router
from app.routes.jobs import router as jobs_router
from app.routes.markets import router as markets_router
from app.routes.source_status import router as source_status_router
from app.routes.trends import router as trends_router
from app.routes.user_features import router as user_features_router
from app.workers.market_sync import sync_market
from app.workers.scheduler import MarketScheduler

class ServiceStatus(BaseModel):
    service: str
    status: str
    data_mode: str

settings = get_settings()
scheduler = MarketScheduler(sync_market, settings.market_sync_interval_seconds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.market_sync_enabled:
        await scheduler.start()
    yield
    await scheduler.stop()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Accept", "Content-Type", "Authorization"])
app.include_router(markets_router, prefix=settings.api_prefix)
app.include_router(gifts_router, prefix=settings.api_prefix)
app.include_router(arbitrage_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(trends_router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
app.include_router(source_status_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(user_features_router, prefix=settings.api_prefix)

@app.get("/health", response_model=ServiceStatus)
@app.get("/api/health", response_model=ServiceStatus)
async def health() -> ServiceStatus:
    return ServiceStatus(service=settings.app_name, status="ok", data_mode="live-only")
