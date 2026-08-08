from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AssistantUnavailable, OpenRouterClient
from app.ai.context import gift_context, market_context
from app.ai.limits import RateLimiter, TTLCache
from app.ai.prompts import CHAT_SYSTEM, VERDICT_SYSTEM
from app.core.auth import current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/ai", tags=["ai"])

_settings = get_settings()
limiter = RateLimiter(_settings.ai_requests_per_hour)
# A verdict is expensive and the market moves slower than a page refresh.
verdict_cache = TTLCache(_settings.ai_verdict_cache_seconds)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    gift_id: int | None = None


class AiAnswer(BaseModel):
    answer: str
    model: str
    remaining: int
    cached: bool = False
    grounded_in: str = "persisted market data"


class AiStatus(BaseModel):
    enabled: bool
    model: str | None = None
    hourly_limit: int


def _client() -> OpenRouterClient:
    client = OpenRouterClient()
    if not client.configured:
        raise HTTPException(503, "AI is not configured: set OPENROUTER_API_KEY")
    return client


def _spend(user: User) -> None:
    if not limiter.allow(user.id):
        raise HTTPException(429, "AI request limit reached for this hour")


@router.get("/status", response_model=AiStatus)
async def status() -> AiStatus:
    """Lets the UI hide the assistant instead of showing a dead button."""
    settings = get_settings()
    enabled = bool(settings.openrouter_api_key)
    return AiStatus(
        enabled=enabled,
        model=settings.openrouter_model if enabled else None,
        hourly_limit=settings.ai_requests_per_hour,
    )


@router.post("/ask", response_model=AiAnswer)
async def ask(
    body: AskRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> AiAnswer:
    """Answer a market question using stored data only."""
    client = _client()
    _spend(user)
    context = await market_context(session)
    if body.gift_id is not None:
        focus = await gift_context(session, body.gift_id)
        if focus:
            context = f"{focus}\n\nWIDER MARKET:\n{context}"
    try:
        reply = await client.complete(
            system=CHAT_SYSTEM,
            user=f"DATA:\n{context}\n\nQUESTION:\n{body.question.strip()}",
        )
    except AssistantUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return AiAnswer(answer=reply.text, model=reply.model, remaining=limiter.remaining(user.id))


@router.get("/gifts/{gift_id}/verdict", response_model=AiAnswer)
async def verdict(
    gift_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> AiAnswer:
    """A short read on whether this gift is worth buying at the current floor."""
    client = _client()
    cached = verdict_cache.get(str(gift_id))
    if cached is not None:
        return AiAnswer(
            answer=cached,
            model=get_settings().openrouter_model,
            remaining=limiter.remaining(user.id),
            cached=True,
        )
    context = await gift_context(session, gift_id)
    if context is None:
        raise HTTPException(404, "Gift not found")
    _spend(user)
    try:
        reply = await client.complete(
            system=VERDICT_SYSTEM,
            user=f"DATA:\n{context}",
            max_tokens=320,
        )
    except AssistantUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    verdict_cache.set(str(gift_id), reply.text)
    return AiAnswer(answer=reply.text, model=reply.model, remaining=limiter.remaining(user.id))
