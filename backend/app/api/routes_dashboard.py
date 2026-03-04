from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.listing import Listing
from app.models.marketplace import PushLog
from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.supplier import SupplierProduct
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    total_products: int
    total_opportunities: int
    a_launch_count: int
    total_listings: int
    total_pushes: int
    total_supplier_products: int
    avg_score: float


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_opportunities = db.query(func.count(Opportunity.id)).scalar() or 0
    a_launch = db.query(func.count(Opportunity.id)).filter(
        Opportunity.decision == "A_launch"
    ).scalar() or 0
    total_listings = db.query(func.count(Listing.id)).scalar() or 0
    total_pushes = db.query(func.count(PushLog.id)).filter(
        PushLog.status == "success"
    ).scalar() or 0
    total_sp = db.query(func.count(SupplierProduct.id)).scalar() or 0
    avg_score = db.query(func.avg(Opportunity.score)).scalar() or 0

    return DashboardStats(
        total_products=total_products,
        total_opportunities=total_opportunities,
        a_launch_count=a_launch,
        total_listings=total_listings,
        total_pushes=total_pushes,
        total_supplier_products=total_sp,
        avg_score=round(float(avg_score), 1),
    )
