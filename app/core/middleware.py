import logging
import time

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.ratelimit import TokenBucket

logger = logging.getLogger(__name__)

# Never throttle these: health is for the orchestrator, and the auth handshake
# has to work even for someone who just burned their quota.
EXEMPT_PATHS = ("/health", "/api/health", "/docs", "/openapi.json", "/api/auth/telegram")
PRUNE_EVERY_SECONDS = 300


def client_key(request: Request) -> str:
    """Identify the caller.

    A signed user id is stable and cannot be spoofed by rotating addresses,
    so it is preferred. Guests fall back to the network address.
    """
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1]
        try:
            # Only reading the subject; the auth dependency does the real check.
            payload = jwt.decode(token, options={"verify_signature": False})
            subject = payload.get("sub")
            if subject:
                return f"user:{subject}"
        except jwt.PyJWTError:
            pass
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # First entry is the original client, the rest are proxies.
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Caps how fast one caller can hit the API.

    Reads and writes get separate budgets: a write is rarer and more
    expensive to get wrong, so it is held to a tighter limit.
    """

    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.reads = TokenBucket(
            rate_per_minute=settings.rate_limit_per_minute,
            burst=settings.rate_limit_burst,
        )
        self.writes = TokenBucket(
            rate_per_minute=settings.write_rate_limit_per_minute,
            burst=max(5, settings.write_rate_limit_per_minute // 2),
        )
        self.enabled = settings.rate_limit_enabled
        self._last_prune = time.monotonic()

    def _maybe_prune(self) -> None:
        now = time.monotonic()
        if now - self._last_prune < PRUNE_EVERY_SECONDS:
            return
        self._last_prune = now
        self.reads.prune()
        self.writes.prune()

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        self._maybe_prune()
        bucket = self.reads if request.method in ("GET", "HEAD", "OPTIONS") else self.writes
        key = client_key(request)
        allowed, remaining, retry_after = bucket.take(key)
        if not allowed:
            logger.info("rate limited", extra={"client": key, "path": request.url.path})
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests, slow down"},
                headers={
                    "Retry-After": str(max(1, int(retry_after) + 1)),
                    "RateLimit-Limit": str(bucket.rate_per_minute),
                    "RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["RateLimit-Limit"] = str(bucket.rate_per_minute)
        response.headers["RateLimit-Remaining"] = str(remaining)
        return response
