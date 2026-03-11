"""Sourcing search models — track web sourcing searches and results."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SourcingSearch(Base):
    __tablename__ = "sourcing_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), default="")
    search_type: Mapped[str] = mapped_column(String(50), default="web")  # web, csv, manual
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, running, completed, failed
    total_products: Mapped[int] = mapped_column(Integer, default=0)
    products_checked: Mapped[int] = mapped_column(Integer, default=0)
    matches_found: Mapped[int] = mapped_column(Integer, default=0)
    profitable_count: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    results = relationship("SourcingResult", back_populates="search", cascade="all, delete-orphan")


class SourcingResult(Base):
    __tablename__ = "sourcing_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_searches.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asin: Mapped[str] = mapped_column(String(10), index=True)

    source_name: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    source_price_ht: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    source_shipping: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    source_currency: Mapped[str] = mapped_column(String(10), default="EUR")
    source_title: Mapped[str] = mapped_column(String(500), default="")
    source_in_stock: Mapped[bool | None] = mapped_column(nullable=True)

    amazon_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    referral_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    fulfillment_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    net_profit: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    margin_pct: Mapped[float] = mapped_column(Float, default=0)
    roi_pct: Mapped[float] = mapped_column(Float, default=0)

    match_type: Mapped[str] = mapped_column(String(20), default="asin")  # asin, ean, title
    match_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    search = relationship("SourcingSearch", back_populates="results")
