from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.overview import OverviewRepository
from app.db.session import get_session
from app.schemas.frontend import OverviewStats

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewStats)
async def overview(session: AsyncSession = Depends(get_session)):
    """Dashboard headline numbers. Reads the database, never the market."""
    return OverviewStats(**await OverviewRepository(session).stats())
