import os
os.environ["MARKET_SYNC_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["JWT_SECRET"] = "integration-test-secret"

from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.models import Gift
from app.db.session import get_session
from app.main import app


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(Gift(canonical_id="canonical:test-gift", name="Test Gift"))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def client(db_session):
    async def override_session():
        yield db_session
    app.dependency_overrides[get_session] = override_session
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def authenticate(client: AsyncClient, telegram_id: int):
    import app.routes.auth as auth_route
    auth_route.validate_telegram_init_data = lambda _: {"id": telegram_id, "username": f"user{telegram_id}", "first_name": "Test"}
    response = await client.post("/api/auth/telegram", json={"init_data": "integration"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_auth_watchlist_portfolio_alerts_are_user_scoped(client):
    token_a = await authenticate(client, 101)
    token_b = await authenticate(client, 202)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert (await client.get("/api/auth/me", headers=headers_a)).json()["telegram_id"] == 101
    assert (await client.post("/api/watchlist/1", headers=headers_a)).status_code == 201
    assert (await client.get("/api/watchlist", headers=headers_a)).json()["items"][0]["gift_id"] == 1
    assert (await client.get("/api/watchlist", headers=headers_b)).json()["items"] == []

    wallet = await client.post("/api/portfolio/wallets", headers=headers_a, json={"address": "EQintegrationwallet123", "label": "Main"})
    assert wallet.status_code == 201
    assert (await client.get("/api/portfolio/wallets", headers=headers_b)).json()["items"] == []

    alert = await client.post("/api/alerts/rules", headers=headers_a, json={"gift_id": 1, "rule_type": "price_below", "threshold": "10"})
    assert alert.status_code == 201
    assert (await client.get("/api/alerts/rules", headers=headers_b)).json()["items"] == []


@pytest.mark.asyncio
async def test_protected_user_routes_require_bearer(client):
    response = await client.get("/api/watchlist")
    assert response.status_code == 401
