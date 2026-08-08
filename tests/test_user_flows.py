import os
os.environ["MARKET_SYNC_ENABLED"] = "false"
os.environ["PORTFOLIO_SYNC_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["JWT_SECRET"] = "integration-test-secret"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.models import AlertEvent, Gift
from app.db.session import get_session
from app.main import app

@pytest_asyncio.fixture
async def user_client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(Gift(canonical_id="canonical:flow-gift", name="Flow Gift"))
        await session.commit()
        async def override_session():
            yield session
        app.dependency_overrides[get_session] = override_session
        async def fake_init_data(_: str):
            return {"id": 9001, "username": "flow_user", "first_name": "Flow"}
        monkeypatch.setattr("app.routes.auth.validate_telegram_init_data", fake_init_data)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_authenticated_user_flow(user_client):
    client, session = user_client
    auth = await client.post("/api/auth/telegram", json={"init_data": "test"})
    assert auth.status_code == 200
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    assert (await client.get("/api/auth/me", headers=headers)).status_code == 200
    assert (await client.post("/api/watchlist/1", headers=headers)).status_code == 201
    assert (await client.get("/api/watchlist", headers=headers)).json()["items"][0]["gift_id"] == 1

    wallet = await client.post("/api/portfolio/wallets", headers=headers, json={"address": "EQflow-wallet-address", "label": "Main"})
    assert wallet.status_code == 201
    assert (await client.get("/api/portfolio/wallets", headers=headers)).json()["items"][0]["label"] == "Main"

    rule = await client.post("/api/alerts/rules", headers=headers, json={"rule_type": "portfolio_change_percent", "threshold": "5"})
    assert rule.status_code == 201
    rule_id = rule.json()["id"]
    assert (await client.patch(f"/api/alerts/rules/{rule_id}", headers=headers, json={"is_active": False})).json()["is_active"] is False

    event = AlertEvent(rule_id=rule_id, user_id=1, message="Portfolio changed", observed_value="5")
    session.add(event)
    await session.commit()
    event_response = await client.get("/api/alerts/events", headers=headers)
    assert event_response.status_code == 200
    event_id = event_response.json()["items"][0]["id"]
    assert (await client.patch(f"/api/alerts/events/{event_id}/read", headers=headers)).json()["is_read"] is True

    assert (await client.delete("/api/watchlist/1", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/portfolio/wallets/{wallet.json()['id']}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/alerts/rules/{rule_id}", headers=headers)).status_code == 204
