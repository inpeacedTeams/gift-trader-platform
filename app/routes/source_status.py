from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import SourceStatusRepository
from app.db.session import get_session

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("/status")
async def source_status(session: AsyncSession = Depends(get_session)):
    statuses = await SourceStatusRepository(session).list()
    return {
        "data_mode": "live-only",
        "sources": [
            {
                "marketplace": item.marketplace,
                "status": item.status,
                "last_attempt_at": item.last_attempt_at,
                "last_success_at": item.last_success_at,
                "last_error": item.last_error,
                "listings_count": item.listings_count,
            }
            for item in statuses
        ],
    }
