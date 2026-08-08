"""Sliding window rate limiting.

Written in process rather than pulled from a library: the API runs as a
single instance today, and one small file beats a dependency plus Redis for
that. Swap the store for Redis before running more than one worker, the
interface is deliberately narrow.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

# Paths that must answer even under pressure, or that cost nothing.
EXEMPT_PREFIXES = ("/health", "/api/health", "/docs", "/openapi.json", "/redoc")


@dataclass(frozen=True)
class Budget:
    limit: int
    window_seconds: int


class SlidingWindow:
    """Counts hits per key, dropping anything older than the window."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        """Drop idle keys so a long uptime does not leak memory."""
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        for key in [key for key, hits in self._hits.items() if not hits]:
            del self._hits[key]

    def check(self, key: str, budget: Budget) -> tuple[bool, int, int]:
        """Returns allowed, remaining and seconds until the window frees up."""
        now = time.monotonic()
        self._sweep(now)
        hits = self._hits[key]
        while hits and now - hits[0] > budget.window_seconds:
            hits.popleft()
        if len(hits) >= budget.limit:
            retry_after = int(budget.window_seconds - (now - hits[0])) + 1
            return False, 0, max(1, retry_after)
        hits.append(now)
        return True, budget.limit - len(hits), 0


def client_key(request: Request) -> str:
    """Identify the caller.

    A signed user id is the fairest key: several people behind one office IP
    should not share a budget. Guests fall back to the address, trusting the
    proxy header only for its first hop.
    """
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                header.split(" ", 1)[1],
                get_settings().jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except jwt.PyJWTError:
            pass
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Caps how fast one caller can hit the API."""

    def __init__(self, app, read: Budget, write: Budget):
        super().__init__(app)
        self.read = read
        self.write = write
        self.window = SlidingWindow()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        budget = self.read if request.method == "GET" else self.write
        key = f"{client_key(request)}:{'r' if request.method == 'GET' else 'w'}"
        allowed, remaining, retry_after = self.window.check(key, budget)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests, slow down"},
                headers={
                    "Retry-After": str(retry_after),
                    "RateLimit-Limit": str(budget.limit),
                    "RateLimit-Remaining": "0",
                    "RateLimit-Reset": str(retry_after),
                },
            )
        response: Response = await call_next(request)
        response.headers["RateLimit-Limit"] = str(budget.limit)
        response.headers["RateLimit-Remaining"] = str(remaining)
        return response
