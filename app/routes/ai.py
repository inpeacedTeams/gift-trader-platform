from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AiUnavailable, OpenRouterClient
from app.ai.context import gift_context, market_context
from app.ai.prompts import SYSTEM_PROMPT, VERDICT_PROMPT
from app.ai.quota import DailyQuota
from app.core.auth import current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/ai", tags=["ai"])
settings = get_settings()
client = OpenRouterClient(settings)
quota = DailyQuota(settings.ai_daily_limit_per_user)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AiAnswer(BaseModel):
    answer: str
    model: str
    remaining_today: int


class AiStatus(BaseModel):
    enabled: bool
    model: str | None = None


def _guard(user: User) -> None:
    if not client.enabled:
        raise HTTPException(503, "Assistant is not configured")
    if not quota.consume(user.id):
        raise HTTPException(429, "Daily assistant limit reached, try again tomorrow")


@router.get("/status", response_model=AiStatus)
async def status() -> AiStatus:
    return AiStatus(enabled=client.enabled, model=settings.openrouter_model if client.enabled else None)


@router.post("/ask", response_model=AiAnswer)
async def ask(
    body: Question,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Answer a market question strictly from what we stored."""
    _guard(user)
    context = await market_context(session)
    prompt = f"ДАННЫЕ РЫНКА:\n{context}\n\nВОПРОС: {body.question.strip()}"
    try:
        answer = await client.complete(system=SYSTEM_PROMPT, user=prompt)
    except AiUnavailable as exc:
        raise HTTPException(503, exc.reason) from exc
    return AiAnswer(answer=answer.text, model=answer.model, remaining_today=quota.remaining(user.id))


@router.get("/gifts/{gift_id}/verdict", response_model=AiAnswer)
async def verdict(
    gift_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Short read on one gift: worth buying, fair, or overpriced."""
    _guard(user)
    context = await gift_context(session, gift_id)
    if context is None:
        raise HTTPException(404, "Gift not found")
    try:
        answer = await client.complete(system=VERDICT_PROMPT, user=context, max_tokens=300)
    except AiUnavailable as exc:
        raise HTTPException(503, exc.reason) from exc
    return AiAnswer(answer=answer.text, model=answer.model, remaining_today=quota.remaining(user.id))
