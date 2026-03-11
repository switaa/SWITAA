"""Alerts and monitoring endpoints for price/stock changes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertItem(BaseModel):
    type: str
    asin: str | None = None
    product_id: str | None = None
    source_url: str | None = None
    old_price: float | None = None
    new_price: float | None = None
    change_pct: float | None = None
    new_margin_pct: float | None = None
    reason: str | None = None
    severity: str = "info"


class PriceCheckResponse(BaseModel):
    products_checked: int
    prices_updated: int
    alerts_generated: int
    errors: int
    alerts: list[AlertItem]


class StockCheckResponse(BaseModel):
    products_checked: int
    out_of_stock: int
    back_in_stock: int
    errors: int
    alerts: list[AlertItem]


class MonitoringSummary(BaseModel):
    total_active_opportunities: int
    total_live_listings: int
    total_products_monitored: int
    avg_margin_pct: float
    products_at_risk: int


@router.post("/run-price-check", response_model=PriceCheckResponse)
async def run_price_check(
    margin_threshold: float = Query(15.0, ge=0),
    price_drop_threshold: float = Query(10.0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a price check on all active opportunities via SP-API."""
    from app.services.price_monitor_service import run_price_check as _run

    stats = await _run(
        db=db,
        margin_threshold=margin_threshold,
        price_drop_threshold=price_drop_threshold,
    )
    return PriceCheckResponse(
        products_checked=stats["products_checked"],
        prices_updated=stats["prices_updated"],
        alerts_generated=stats["alerts_generated"],
        errors=stats["errors"],
        alerts=[AlertItem(**a) for a in stats.get("alerts", [])],
    )


@router.post("/run-stock-check", response_model=StockCheckResponse)
async def run_stock_check(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a stock availability check on source supplier URLs."""
    from app.services.stock_monitor_service import run_stock_check as _run

    stats = await _run(db=db)
    return StockCheckResponse(
        products_checked=stats["products_checked"],
        out_of_stock=stats["out_of_stock"],
        back_in_stock=stats["back_in_stock"],
        errors=stats["errors"],
        alerts=[AlertItem(**a) for a in stats.get("alerts", [])],
    )


@router.get("/summary", response_model=MonitoringSummary)
def get_monitoring_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a summary of the current monitoring state."""
    from sqlalchemy import func

    from app.models.listing import Listing
    from app.models.opportunity import Opportunity
    from app.models.product import Product

    active_opps = (
        db.query(func.count(Opportunity.id))
        .filter(Opportunity.decision.in_(["A_launch", "B_review"]))
        .scalar()
    ) or 0

    live_listings = (
        db.query(func.count(Listing.id))
        .filter(Listing.marketplace_status == "live")
        .scalar()
    ) or 0

    monitored = (
        db.query(func.count(Product.id))
        .filter(Product.status != "archived")
        .filter(Product.source == "tactical_arbitrage")
        .scalar()
    ) or 0

    avg_margin = (
        db.query(func.avg(Opportunity.margin_pct))
        .filter(Opportunity.decision.in_(["A_launch", "B_review"]))
        .scalar()
    ) or 0.0

    at_risk = (
        db.query(func.count(Opportunity.id))
        .filter(Opportunity.decision.in_(["A_launch", "B_review"]))
        .filter(Opportunity.margin_pct < 15)
        .scalar()
    ) or 0

    return MonitoringSummary(
        total_active_opportunities=active_opps,
        total_live_listings=live_listings,
        total_products_monitored=monitored,
        avg_margin_pct=round(float(avg_margin), 1),
        products_at_risk=at_risk,
    )
