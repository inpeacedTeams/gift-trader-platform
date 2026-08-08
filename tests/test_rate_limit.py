import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.rate_limit import Budget, RateLimitMiddleware, SlidingWindow


def build_app(read: int = 3, write: int = 1) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, read=Budget(read, 60), write=Budget(write, 60))

    @app.get("/api/gifts")
    async def gifts():
        return {"ok": True}

    @app.post("/api/watchlist/1")
    async def save():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


async def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_window_blocks_past_the_budget():
    window = SlidingWindow()
    budget = Budget(2, 60)

    assert window.check("a", budget)[0] is True
    assert window.check("a", budget)[0] is True
    allowed, remaining, retry_after = window.check("a", budget)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_window_keys_are_independent():
    window = SlidingWindow()
    budget = Budget(1, 60)
    window.check("a", budget)

    assert window.check("b", budget)[0] is True


@pytest.mark.asyncio
async def test_reads_are_capped_and_reported():
    async with await client(build_app(read=2)) as http:
        first = await http.get("/api/gifts")
        second = await http.get("/api/gifts")
        third = await http.get("/api/gifts")

    assert first.status_code == 200
    assert first.headers["RateLimit-Remaining"] == "1"
    assert second.status_code == 200
    assert third.status_code == 429
    assert int(third.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_writes_have_their_own_budget():
    async with await client(build_app(read=5, write=1)) as http:
        await http.post("/api/watchlist/1")
        blocked = await http.post("/api/watchlist/1")
        # Reads still work: a spent write budget must not lock the app.
        readable = await http.get("/api/gifts")

    assert blocked.status_code == 429
    assert readable.status_code == 200


@pytest.mark.asyncio
async def test_health_is_never_limited():
    async with await client(build_app(read=1)) as http:
        for _ in range(5):
            response = await http.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_signed_in_users_get_their_own_budget():
    token = jwt.encode({"sub": "42"}, get_settings().jwt_secret, algorithm="HS256")
    async with await client(build_app(read=1)) as http:
        await http.get("/api/gifts")
        # Same address, different identity, so the budget is not shared.
        signed_in = await http.get("/api/gifts", headers={"Authorization": f"Bearer {token}"})

    assert signed_in.status_code == 200
