import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SearchCampaign(Base):
    __tablename__ = "search_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str] = mapped_column(String(50), index=True)
    sub_niche: Mapped[str] = mapped_column(String(100), default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    marketplace: Mapped[str] = mapped_column(String(50), default="amazon_fr")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    phase: Mapped[str] = mapped_column(String(50), default="")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    target_count: Mapped[int] = mapped_column(Integer, default=50)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    results = relationship("SearchResult", back_populates="campaign", cascade="all, delete-orphan")


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_campaigns.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    keyword: Mapped[str] = mapped_column(String(255), default="")
    rank_at_discovery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="")
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    campaign = relationship("SearchCampaign", back_populates="results")
    product = relationship("Product")
