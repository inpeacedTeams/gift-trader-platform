from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.events import EVENT_TYPES, EventRepository
from app.db.session import get_session
from app.schemas.frontend import MarketEventCard, MarketEventFeed

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=MarketEventFeed)
async def events(
    limit: int = Query(default=40, ge=1, le=200),
    after_id: int | None = Query(default=None, ge=0),
    event_type: str | None = Query(default=None, pattern=f"^({'|'.join(EVENT_TYPES)})$"),
    gift_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    """What changed on the market, newest first."""
    rows = await EventRepository(session).feed(
        limit=limit, after_id=after_id, event_type=event_type, gift_id=gift_id
    )
    items = [MarketEventCard(**row) for row in rows]
    return MarketEventFeed(items=items, latest_id=items[0].id if items else after_id)
