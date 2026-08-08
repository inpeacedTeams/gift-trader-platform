from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import OpenRouterClient, OpenRouterError
from app.ai.context import chat_context, gift_context
from app.ai.limits import RateLimiter, TTLCache
from app.ai.prompts import CHAT_SYSTEM, VERDICT_SYSTEM
from app.core.auth import current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/assistant", tags=["assistant"])

settings = get_settings()
limiter = RateLimiter(settings.ai_hourly_limit)
verdict_cache = TTLCache(settings.ai_verdict_cache_seconds)


def build_client() -> OpenRouterClient:
    current = get_settings()
    return OpenRouterClient(
        current.openrouter_api_key,
        base_url=current.openrouter_base_url,
        model=current.openrouter_model,
    )


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    model: str
    remaining: int


class VerdictResponse(BaseModel):
    gift_id: int
    verdict: str
    model: str
    cached: bool = False


class AssistantStatus(BaseModel):
    enabled: bool
    model: str | None = None
    hourly_limit: int


@router.get("/status", response_model=AssistantStatus)
async def status() -> AssistantStatus:
    """Lets the interface hide the assistant instead of failing on click."""
    current = get_settings()
    enabled = bool(current.openrouter_api_key)
    return AssistantStatus(
        enabled=enabled,
        model=current.openrouter_model if enabled else None,
        hourly_limit=current.ai_hourly_limit,
    )


def _guard(user: User) -> int:
    allowed, remaining = limiter.check(user.id)
    if not allowed:
        raise HTTPException(429, "Hourly AI limit reached, try again later")
    return remaining


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    client = build_client()
    if not client.configured:
        raise HTTPException(503, "AI assistant is not configured")
    remaining = _guard(user)
    context = await chat_context(session)
    try:
        answer = await client.complete(
            [
                {"role": "system", "content": CHAT_SYSTEM},
                {"role": "user", "content": f"MARKET DATA:\n{context}\n\nQUESTION: {body.question}"},
            ]
        )
    except OpenRouterError as exc:
        raise HTTPException(502, str(exc)) from exc
    return ChatResponse(answer=answer, model=client.model, remaining=remaining)


@router.get("/gifts/{gift_id}/verdict", response_model=VerdictResponse)
async def verdict(
    gift_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> VerdictResponse:
    client = build_client()
    if not client.configured:
        raise HTTPException(503, "AI assistant is not configured")
    cached = verdict_cache.get(str(gift_id))
    if cached is not None:
        return VerdictResponse(gift_id=gift_id, verdict=cached, model=client.model, cached=True)
    context = await gift_context(session, gift_id)
    if context is None:
        raise HTTPException(404, "Gift not found")
    _guard(user)
    try:
        answer = await client.complete(
            [
                {"role": "system", "content": VERDICT_SYSTEM},
                {"role": "user", "content": f"MARKET DATA:\n{context}"},
            ],
            max_tokens=220,
        )
    except OpenRouterError as exc:
        raise HTTPException(502, str(exc)) from exc
    verdict_cache.set(str(gift_id), answer)
    return VerdictResponse(gift_id=gift_id, verdict=answer, model=client.model)
