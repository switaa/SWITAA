"""Sourcing API — web search, CSV import, results dashboard."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import Product
from app.models.sourcing import SourcingResult, SourcingSearch
from app.models.user import User

router = APIRouter(prefix="/api/v1/sourcing", tags=["sourcing"])


class SourcingSearchOut(BaseModel):
    id: UUID
    name: str
    search_type: str
    status: str
    total_products: int
    products_checked: int
    matches_found: int
    profitable_count: int
    created_at: str
    completed_at: str | None = None

    model_config = {"from_attributes": True}


class SourcingResultOut(BaseModel):
    id: UUID
    asin: str
    product_title: str | None = None
    product_image: str | None = None
    source_name: str
    source_url: str
    source_price: float
    source_price_ht: float | None
    amazon_price: float
    net_profit: float
    margin_pct: float
    roi_pct: float
    match_type: str
    match_confidence: float
    source_in_stock: bool | None = None

    model_config = {"from_attributes": True}


class SourcingStats(BaseModel):
    total_searches: int
    total_matches: int
    profitable_matches: int
    best_roi: float
    avg_margin: float


@router.get("/searches", response_model=list[SourcingSearchOut])
def list_searches(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    searches = (
        db.query(SourcingSearch)
        .order_by(SourcingSearch.created_at.desc())
        .limit(20)
        .all()
    )
    out = []
    for s in searches:
        out.append(SourcingSearchOut(
            id=s.id,
            name=s.name,
            search_type=s.search_type,
            status=s.status,
            total_products=s.total_products,
            products_checked=s.products_checked,
            matches_found=s.matches_found,
            profitable_count=s.profitable_count,
            created_at=s.created_at.isoformat() if s.created_at else "",
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        ))
    return out


@router.get("/results", response_model=list[SourcingResultOut])
def list_results(
    search_id: UUID | None = None,
    profitable_only: bool = False,
    min_roi: float = Query(default=0),
    sort_by: str = Query(default="roi", pattern="^(roi|margin|profit|price)$"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(SourcingResult).join(
        Product, SourcingResult.product_id == Product.id, isouter=True
    )

    if search_id:
        q = q.filter(SourcingResult.search_id == search_id)
    if profitable_only:
        q = q.filter(SourcingResult.net_profit > 0)
    if min_roi > 0:
        q = q.filter(SourcingResult.roi_pct >= min_roi)

    order_map = {
        "roi": SourcingResult.roi_pct.desc(),
        "margin": SourcingResult.margin_pct.desc(),
        "profit": SourcingResult.net_profit.desc(),
        "price": SourcingResult.source_price.asc(),
    }
    q = q.order_by(order_map.get(sort_by, SourcingResult.roi_pct.desc()))
    rows = q.limit(limit).all()

    products_by_id = {}
    pids = [r.product_id for r in rows if r.product_id]
    if pids:
        for p in db.query(Product).filter(Product.id.in_(pids)).all():
            products_by_id[p.id] = p

    out = []
    for r in rows:
        p = products_by_id.get(r.product_id)
        out.append(SourcingResultOut(
            id=r.id,
            asin=r.asin,
            product_title=p.title if p else None,
            product_image=p.image_url if p else None,
            source_name=r.source_name,
            source_url=r.source_url,
            source_price=float(r.source_price),
            source_price_ht=float(r.source_price_ht) if r.source_price_ht else None,
            amazon_price=float(r.amazon_price),
            net_profit=float(r.net_profit),
            margin_pct=float(r.margin_pct),
            roi_pct=float(r.roi_pct),
            match_type=r.match_type,
            match_confidence=float(r.match_confidence),
            source_in_stock=r.source_in_stock,
        ))
    return out


@router.get("/stats", response_model=SourcingStats)
def get_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    total_searches = db.query(func.count(SourcingSearch.id)).scalar() or 0
    total_matches = db.query(func.count(SourcingResult.id)).scalar() or 0
    profitable_matches = (
        db.query(func.count(SourcingResult.id))
        .filter(SourcingResult.net_profit > 0)
        .scalar() or 0
    )
    best_roi = (
        db.query(func.max(SourcingResult.roi_pct)).scalar() or 0
    )
    avg_margin = (
        db.query(func.avg(SourcingResult.margin_pct))
        .filter(SourcingResult.net_profit > 0)
        .scalar() or 0
    )
    return SourcingStats(
        total_searches=total_searches,
        total_matches=total_matches,
        profitable_matches=profitable_matches,
        best_roi=round(float(best_roi), 1),
        avg_margin=round(float(avg_margin), 1),
    )


@router.post("/search/web")
async def trigger_web_search(
    background_tasks: BackgroundTasks,
    min_score: float = Query(default=30),
    max_products: int = Query(default=50, le=100),
    _db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    async def _run():
        from app.core.database import SessionLocal
        from app.services.web_sourcing_service import run_web_sourcing
        session = SessionLocal()
        try:
            await run_web_sourcing(
                session,
                user_id=str(user.id),
                min_score=min_score,
                max_products=max_products,
            )
        finally:
            session.close()

    background_tasks.add_task(_run)
    return {"status": "search_started"}


@router.post("/search/csv")
async def upload_csv_pricelist(
    file: UploadFile = File(...),
    source_name: str = Form(default="CSV Import"),
    delimiter: str = Form(default=";"),
    mode: str = Form(default="fbm"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Fichier CSV requis (.csv ou .txt)")

    content = await file.read()
    try:
        csv_text = content.decode("utf-8")
    except UnicodeDecodeError:
        csv_text = content.decode("latin-1")

    from app.services.web_sourcing_service import import_csv_pricelist

    result = import_csv_pricelist(
        db=db,
        csv_content=csv_text,
        source_name=source_name,
        delimiter=delimiter,
        mode=mode,
        user_id=str(user.id),
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.delete("/searches/{search_id}")
def delete_search(
    search_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    search = db.query(SourcingSearch).filter(SourcingSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Recherche non trouvee")
    db.delete(search)
    db.commit()
    return {"status": "deleted"}
