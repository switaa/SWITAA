import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supplier_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_products.id"), nullable=True
    )
    selling_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cost_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    marketplace_fees: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    margin_abs: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    margin_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score: Mapped[float] = mapped_column(Numeric(10, 2), default=0, index=True)
    margin_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    competition_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    demand_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    bsr_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    decision: Mapped[str] = mapped_column(String(20), default="B_review", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    product = relationship("Product", back_populates="opportunities")
    campaign = relationship("SearchCampaign", backref="opportunities")
