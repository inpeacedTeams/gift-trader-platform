from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import verify_secrets
from app.notifications.delivery import deliver_pending_alerts
from app.portfolio.sync import sync_portfolios
from app.routes.ai import router as ai_router
from app.routes.analytics import router as analytics_router
from app.routes.arbitrage import router as arbitrage_router
from app.routes.auth import router as auth_router
from app.routes.collections import router as collections_router
from app.routes.deals import router as deals_router
from app.routes.events import router as events_router
from app.routes.gifts import router as gifts_router
from app.routes.history import router as history_router
from app.routes.jobs import router as jobs_router
from app.routes.markets import router as markets_router
from app.routes.movers import router as movers_router
from app.routes.overview import router as overview_router
from app.routes.portfolio import router as portfolio_router
from app.routes.source_status import router as source_status_router
from app.routes.trends import router as trends_router
from app.routes.user_features import router as user_features_router
from app.workers.market_sync import sync_market
from app.workers.scheduler import MarketScheduler
from app.workers.trade_sync import sync_trades


class ServiceStatus(BaseModel):
    service: str
    status: str
    data_mode: str


settings = get_settings()
# Fails fast in production rather than serving forgeable tokens.
verify_secrets(settings)

market_scheduler = MarketScheduler(sync_market, settings.market_sync_interval_seconds)
trade_scheduler = MarketScheduler(sync_trades, settings.trade_sync_interval_seconds)
portfolio_scheduler = MarketScheduler(sync_portfolios, settings.portfolio_sync_interval_seconds)
notification_scheduler = MarketScheduler(deliver_pending_alerts, 30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.market_sync_enabled:
        await market_scheduler.start()
    if settings.trade_sync_enabled and settings.tonnel_auth_data:
        await trade_scheduler.start()
    if settings.portfolio_sync_enabled:
        await portfolio_scheduler.start()
    if settings.telegram_bot_token:
        await notification_scheduler.start()
    yield
    await market_scheduler.stop()
    await trade_scheduler.stop()
    await portfolio_scheduler.stop()
    await notification_scheduler.stop()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-Admin-Token"],
)
for router in (
    overview_router,
    markets_router,
    gifts_router,
    collections_router,
    deals_router,
    movers_router,
    events_router,
    arbitrage_router,
    analytics_router,
    trends_router,
    history_router,
    source_status_router,
    jobs_router,
    auth_router,
    user_features_router,
    portfolio_router,
    ai_router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", response_model=ServiceStatus)
@app.get("/api/health", response_model=ServiceStatus)
async def health() -> ServiceStatus:
    return ServiceStatus(service=settings.app_name, status="ok", data_mode="live-only")
