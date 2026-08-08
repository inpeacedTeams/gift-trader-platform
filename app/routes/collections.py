from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import CollectionRepository
from app.db.session import get_session
from app.schemas.frontend import CollectionCard, CollectionList

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=CollectionList)
async def collections(
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    rows = await CollectionRepository(session).overview(search=search)
    return CollectionList(items=[CollectionCard(**row) for row in rows])
