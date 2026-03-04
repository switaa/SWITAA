import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asin: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="")
    brand: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(255), default="", index=True)
    marketplace: Mapped[str] = mapped_column(String(50), default="amazon_fr", index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    bsr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    seller_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50), default="keepa", index=True)
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    niche: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sub_niche: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    amazon_is_seller: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    buybox_seller: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buybox_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_stability: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fba_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hazmat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    brand_restricted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    history = relationship("ProductHistory", back_populates="product", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="product", cascade="all, delete-orphan")


class ProductHistory(Base):
    __tablename__ = "product_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    bsr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seller_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    product = relationship("Product", back_populates="history")
