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

    model_config = {"from_attributes": True}


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    min_score: float = Query(0),
    decision: str = Query(None),
    niche: str = Query(None),
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
        )
        .join(Product, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
    )
    if decision:
        q = q.filter(Opportunity.decision == decision)
    if niche:
        q = q.filter(Product.niche == niche)

    rows = q.order_by(Opportunity.score.desc()).offset(offset).limit(limit).all()
    return [
        OpportunityOut(
            id=r.id,
            asin=r.asin,
            title=r.title,
            price=float(r.price),
            cost_price=float(r.cost_price),
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
        )
        for r in rows
    ]
