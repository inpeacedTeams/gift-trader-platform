from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AiUnavailable, OpenRouterClient
from app.ai.context import gift_context, market_overview
from app.ai.limits import RateLimiter
from app.ai.prompts import ASK_PROMPT, VERDICT_PROMPT
from app.core.auth import current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/ai", tags=["ai"])
limiter = RateLimiter(get_settings().ai_requests_per_hour)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    gift_id: int | None = None


class AiAnswer(BaseModel):
    answer: str
    model: str
    grounded_in: str = "persisted market data"
    remaining_today: int | None = None


class AiStatus(BaseModel):
    enabled: bool
    model: str | None = None


def _client() -> OpenRouterClient:
    client = OpenRouterClient()
    if not client.configured:
        raise HTTPException(503, "AI is not configured: set OPENROUTER_API_KEY")
    return client


def _spend(user: User) -> int:
    """Charge one request against the user's budget, or refuse."""
    if not limiter.allow(user.id):
        raise HTTPException(429, "AI request limit reached, try again later")
    return limiter.remaining(user.id)


@router.get("/status", response_model=AiStatus)
async def status():
    """Lets the UI hide the assistant instead of showing a dead button."""
    settings = get_settings()
    enabled = bool(settings.openrouter_api_key)
    return AiStatus(enabled=enabled, model=settings.openrouter_model if enabled else None)


@router.post("/ask", response_model=AiAnswer)
async def ask(
    body: AskRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Answer a market question using stored data only."""
    client = _client()
    remaining = _spend(user)
    context = await market_overview(session)
    if body.gift_id is not None:
        focus = await gift_context(session, body.gift_id)
        if focus:
            context = f"{focus}\n\nWIDER MARKET:\n{context}"
    prompt = f"MARKET DATA:\n{context}\n\nQUESTION:\n{body.question.strip()}"
    try:
        reply = await client.complete(system=ASK_PROMPT, user=prompt)
    except AiUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return AiAnswer(answer=reply.content, model=reply.model, remaining_today=remaining)


@router.get("/gifts/{gift_id}/verdict", response_model=AiAnswer)
async def verdict(
    gift_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """A short read on whether this gift is worth buying at the current floor."""
    client = _client()
    context = await gift_context(session, gift_id)
    if context is None:
        raise HTTPException(404, "Gift not found")
    remaining = _spend(user)
    try:
        reply = await client.complete(
            system=VERDICT_PROMPT,
            user=f"MARKET DATA:\n{context}",
            max_tokens=320,
        )
    except AiUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return AiAnswer(answer=reply.content, model=reply.model, remaining_today=remaining)
