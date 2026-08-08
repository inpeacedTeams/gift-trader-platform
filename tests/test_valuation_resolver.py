from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.models import Collection, Gift
from app.portfolio.valuation import resolve_gift

@pytest.mark.asyncio
async def test_resolver_rejects_ambiguous_match():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        collection = Collection(chain_address="EQcollection")
        session.add(collection); await session.flush()
        session.add_all([Gift(canonical_id="gift:a", collection_id=collection.id, name="Rose", model="Gold"), Gift(canonical_id="gift:b", collection_id=collection.id, name="Rose", model="Gold")]); await session.commit()
        gift, outcome, confidence, candidates = await resolve_gift(session, nft_address="EQunknown", collection_address="EQcollection", metadata={"name":"Rose", "attributes":[{"trait_type":"model","value":"Gold"}]})
        assert gift is None and outcome == "ambiguous_identity" and confidence is None and candidates == 2
    await engine.dispose()

@pytest.mark.asyncio
async def test_resolver_accepts_exact_unique_match():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        collection = Collection(chain_address="EQcollection"); session.add(collection); await session.flush(); gift = Gift(canonical_id="gift:a", collection_id=collection.id, name="Rose", model="Gold"); session.add(gift); await session.commit()
        resolved, outcome, confidence, candidates = await resolve_gift(session, nft_address="EQunknown", collection_address="EQcollection", metadata={"name":"Rose", "attributes":[{"trait_type":"model","value":"Gold"}]})
        assert resolved.id == gift.id and outcome == "collection_name_model_exact" and confidence == Decimal("85") and candidates == 1
    await engine.dispose()
