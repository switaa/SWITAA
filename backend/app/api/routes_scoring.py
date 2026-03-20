from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


class OpportunityOut(BaseModel):
    id: UUID
    asin: str
    title: str
    price: float
    cost_price: float
    margin_pct: float
    score: float
    decision: str
    marketplace: str
    niche: Optional[str] = None
    sub_niche: Optional[str] = None
    competition_score: float = 0
    demand_score: float = 0
    bsr_score: float = 0
    margin_score: float = 0
    seller_count: Optional[int] = None
    source: str = ""
    source_url: Optional[str] = None
    gross_roi: Optional[float] = None
    monthly_sales: Optional[int] = None
    bsr: Optional[int] = None
    est_monthly_revenue: Optional[float] = None
    unlock_priority: Optional[float] = None

    model_config = {"from_attributes": True}


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    min_score: float = Query(0),
    decision: str = Query(None),
    niche: str = Query(None),
    source: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(
            Opportunity.id,
            Product.asin,
            Product.title,
            Product.price,
            Opportunity.cost_price,
            Opportunity.margin_pct,
            Opportunity.score,
            Opportunity.decision,
            Product.marketplace,
            Product.niche,
            Product.sub_niche,
            Opportunity.competition_score,
            Opportunity.demand_score,
            Opportunity.bsr_score,
            Opportunity.margin_score,
            Product.seller_count,
            Product.source,
            Product.raw_data,
            Product.monthly_sales,
            Product.bsr,
            Product.brand_restricted,
        )
        .join(Product, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
    )
    if decision:
        q = q.filter(Opportunity.decision == decision)
    if niche:
        q = q.filter(Product.niche == niche)
    if source:
        q = q.filter(Product.source == source)

    rows = q.order_by(Opportunity.score.desc()).offset(offset).limit(limit).all()
    results = []
    for r in rows:
        raw = r.raw_data or {}
        source_url = raw.get("source_url") or None
        gross_roi = raw.get("ta_gross_roi")

        price = float(r.price) if r.price else 0
        monthly_sales = r.monthly_sales or 0
        est_revenue = round(price * monthly_sales, 2) if monthly_sales else None
        cost_price = float(r.cost_price) if r.cost_price else 0

        unlock_priority = _calc_unlock_priority(
            score=float(r.score),
            monthly_sales=monthly_sales,
            price=price,
            cost_price=cost_price,
            margin_pct=float(r.margin_pct),
            brand_restricted=r.brand_restricted,
        )

        results.append(
            OpportunityOut(
                id=r.id,
                asin=r.asin,
                title=r.title,
                price=price,
                cost_price=cost_price,
                margin_pct=float(r.margin_pct),
                score=float(r.score),
                decision=r.decision,
                marketplace=r.marketplace,
                niche=r.niche,
                sub_niche=r.sub_niche,
                competition_score=float(r.competition_score),
                demand_score=float(r.demand_score),
                bsr_score=float(r.bsr_score),
                margin_score=float(r.margin_score),
                seller_count=r.seller_count,
                source=r.source or "",
                source_url=source_url,
                gross_roi=float(gross_roi) if gross_roi else None,
                monthly_sales=r.monthly_sales,
                bsr=r.bsr,
                est_monthly_revenue=est_revenue,
                unlock_priority=unlock_priority,
            )
        )
    return results


def _calc_unlock_priority(
    score: float,
    monthly_sales: int,
    price: float,
    cost_price: float,
    margin_pct: float,
    brand_restricted: bool | None,
) -> float:
    """Composite priority score (0-100) for deciding which products to unlock first.

    Factors: potential monthly profit, volume, margin quality, restriction penalty.
    """
    monthly_profit = 0.0
    if price > 0 and cost_price > 0:
        unit_profit = price - (price * 0.15) - cost_price
        monthly_profit = unit_profit * monthly_sales

    profit_score = min(100, (monthly_profit / 500) * 100) if monthly_profit > 0 else 0
    volume_score = min(100, (monthly_sales / 200) * 100) if monthly_sales > 0 else 0
    margin_quality = min(100, margin_pct * 2) if margin_pct > 0 else 0

    restriction_penalty = 15 if brand_restricted else 0

    priority = (
        profit_score * 0.40
        + volume_score * 0.25
        + margin_quality * 0.20
        + score * 0.15
        - restriction_penalty
    )
    return round(max(0, min(100, priority)), 1)
