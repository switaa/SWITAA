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
    id: str
    asin: str
    title: str
    price: float
    cost_price: float
    margin_pct: float
    score: float
    decision: str
    marketplace: str

    model_config = {"from_attributes": True}


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    min_score: float = Query(0),
    decision: str = Query(None),
    limit: int = Query(50, le=200),
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
        )
        .join(Product, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
    )
    if decision:
        q = q.filter(Opportunity.decision == decision)

    rows = q.order_by(Opportunity.score.desc()).limit(limit).all()
    return [
        OpportunityOut(
            id=str(r.id), asin=r.asin, title=r.title, price=float(r.price),
            cost_price=float(r.cost_price), margin_pct=float(r.margin_pct),
            score=float(r.score), decision=r.decision, marketplace=r.marketplace,
        )
        for r in rows
    ]
