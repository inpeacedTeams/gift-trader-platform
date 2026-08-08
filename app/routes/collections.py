from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import CollectionRepository
from app.db.session import get_session
from app.schemas.frontend import CollectionCard, CollectionPage

router = APIRouter(prefix="/collections", tags=["collections"])


def _card(row) -> CollectionCard:
    return CollectionCard(
        id=row.id,
        name=row.name,
        slug=row.slug,
        chain_address=row.chain_address,
        gift_count=row.gift_count,
        listings_count=row.listings_count,
        floor_ton=row.floor_ton,
        image_url=row.image_url,
    )


@router.get("", response_model=CollectionPage)
async def collections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=48, ge=1, le=200),
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    rows, total = await CollectionRepository(session).page(page=page, page_size=page_size, search=search)
    return CollectionPage(
        items=[_card(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        has_next=page * page_size < total,
    )


@router.get("/{collection_id}", response_model=CollectionCard)
async def collection_detail(collection_id: int, session: AsyncSession = Depends(get_session)):
    row = await CollectionRepository(session).detail(collection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _card(row)
