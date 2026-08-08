from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .market import Listing


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    chain_address: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    slug: Mapped[str | None] = mapped_column(String(255), index=True)
    gifts: Mapped[list["Gift"]] = relationship(back_populates="collection")


class Gift(Base):
    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id"), index=True
    )
    gift_number: Mapped[int | None] = mapped_column()
    name: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    metadata_uri: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    collection: Mapped[Collection | None] = relationship(back_populates="gifts")
    listings: Mapped[list["Listing"]] = relationship(back_populates="gift")
    __table_args__ = (
        Index("ix_gifts_collection_number", "collection_id", "gift_number"),
    )
