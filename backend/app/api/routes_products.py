import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import Product
from app.models.user import User

logger = logging.getLogger("marcus.routes_products")
router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductOut(BaseModel):
    id: UUID
    asin: str
    title: str
    brand: str
    category: str
    marketplace: str
    price: float
    currency: str
    bsr: Optional[int]
    monthly_sales: Optional[int]
    review_count: Optional[int]
    rating: Optional[float]
    seller_count: Optional[int]
    image_url: str
    source: str
    status: str
    niche: Optional[str] = None
    sub_niche: Optional[str] = None
    amazon_is_seller: Optional[bool] = None
    buybox_seller: Optional[str] = None
    price_stability: Optional[str] = None

    model_config = {"from_attributes": True}


class EnrichResponse(BaseModel):
    status: str
    message: Optional[str] = None
    total_products: int = 0
    batches_processed: int = 0
    enriched: int = 0
    skipped: int = 0
    errors: int = 0
    tokens_before: int = 0
    tokens_after: int = 0
    tokens_left: Optional[int] = None


@router.get("/", response_model=list[ProductOut])
def list_products(
    marketplace: str = Query(None),
    category: str = Query(None),
    status: str = Query(None),
    niche: str = Query(None),
    sub_niche: str = Query(None),
    min_price: float = Query(None),
    max_price: float = Query(None),
    sort_by: str = Query("created_at"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Product)
    if marketplace:
        q = q.filter(Product.marketplace == marketplace)
    if category:
        q = q.filter(Product.category == category)
    if status:
        q = q.filter(Product.status == status)
    if niche:
        q = q.filter(Product.niche == niche)
    if sub_niche:
        q = q.filter(Product.sub_niche == sub_niche)
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)

    order_col = getattr(Product, sort_by, Product.created_at)
    return q.order_by(order_col.desc()).offset(offset).limit(limit).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()


@router.post("/enrich", response_model=EnrichResponse)
async def enrich_products(
    source: str = Query(default="helium10_blackbox"),
    marketplace: str = Query(default="amazon_fr"),
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger Keepa enrichment on products matching the source filter.

    Fetches BuyBox info, price stability, BSR trends from Keepa for each
    product.  Only products missing enrichment data are processed unless
    *force=True*.
    """
    from app.services.enrichment_service import run_keepa_enrichment

    try:
        result = await run_keepa_enrichment(
            db=db,
            source_filter=source,
            marketplace=marketplace,
            force=force,
        )
        return EnrichResponse(**result)
    except Exception as e:
        logger.exception("Keepa enrichment error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class SPAPIEnrichResponse(BaseModel):
    status: str
    message: Optional[str] = None
    total: int = 0
    enriched: int = 0
    errors: int = 0
    remaining: int = 0


@router.post("/enrich-spapi", response_model=SPAPIEnrichResponse)
async def enrich_products_spapi(
    source: str = Query(default="helium10_blackbox"),
    force: bool = Query(default=False),
    max_products: int = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enrich products with FREE SP-API data (BuyBox, competitive pricing)."""
    from app.services.spapi_enrichment_service import run_spapi_enrichment

    try:
        result = await run_spapi_enrichment(
            db=db, source_filter=source, force=force, max_products=max_products,
        )
        return SPAPIEnrichResponse(**result)
    except Exception as e:
        logger.exception("SP-API enrichment error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class ProfitabilityResponse(BaseModel):
    updated: int
    target_margin_pct: float
    mode: str = "fbm"


@router.post("/recalc-profitability", response_model=ProfitabilityResponse)
def recalculate_profitability(
    target_margin_pct: float = Query(default=35.0),
    mode: str = Query(default="fbm", pattern="^(fba|fbm)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recalculate fees and profitability for all opportunities (FBA or FBM mode)."""
    from app.services.profitability_service import enrich_opportunities_with_profitability

    result = enrich_opportunities_with_profitability(db, target_margin_pct, mode=mode)
    return ProfitabilityResponse(**result)


class ProfitCalcRequest(BaseModel):
    selling_price: float
    cost_price: float
    weight_kg: Optional[float] = None
    longest_side_cm: Optional[float] = None
    shipping_to_fba: float = 1.50
    mode: str = "fbm"


class ProfitCalcResponse(BaseModel):
    selling_price: float
    cost_price: float
    referral_fee: float
    fulfillment_fee: float
    shipping_cost: float
    total_fees: float
    net_profit: float
    margin_pct: float
    roi: float
    break_even_cost: float
    mode: str = "fbm"


@router.post("/calc-profit", response_model=ProfitCalcResponse)
def calc_profit(
    req: ProfitCalcRequest,
    user: User = Depends(get_current_user),
):
    """Calculate profitability for a single product (FBA or FBM mode)."""
    from app.services.profitability_service import calculate_profitability

    result = calculate_profitability(
        selling_price=req.selling_price,
        cost_price=req.cost_price,
        weight_kg=req.weight_kg,
        longest_side_cm=req.longest_side_cm,
        shipping_to_fba=req.shipping_to_fba,
        mode=req.mode,
    )
    return ProfitCalcResponse(**result)


class TopProductOut(BaseModel):
    id: UUID
    asin: str
    title: str
    brand: str
    niche: Optional[str]
    price: float
    buybox_price: Optional[float]
    bsr: Optional[int]
    monthly_sales: Optional[int]
    seller_count: Optional[int]
    review_count: Optional[int]
    rating: Optional[float]
    amazon_is_seller: Optional[bool]
    score: float
    max_cost_price: float
    total_fees: float
    image_url: str

    model_config = {"from_attributes": True}


@router.get("/top", response_model=list[TopProductOut])
def get_top_products(
    min_score: float = Query(default=40.0),
    max_bsr: int = Query(default=100000),
    target_margin: float = Query(default=35.0),
    exclude_amazon_seller: bool = Query(default=True),
    mode: str = Query(default="fbm", pattern="^(fba|fbm)$"),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get top products filtered by score, BSR, and Amazon-as-seller."""
    from app.services.profitability_service import calculate_profitability

    q = (
        db.query(Product, Opportunity.score)
        .join(Opportunity, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
        .filter(Product.price > 0)
    )

    if max_bsr:
        q = q.filter((Product.bsr <= max_bsr) | (Product.bsr.is_(None)))
    if exclude_amazon_seller:
        q = q.filter((Product.amazon_is_seller == False) | (Product.amazon_is_seller.is_(None)))

    rows = q.order_by(Opportunity.score.desc()).limit(limit).all()

    results = []
    for product, score in rows:
        selling_price = float(product.buybox_price or product.price)
        raw = product.raw_data or {}
        weight = raw.get("weight")
        longest = None
        for k in ("length", "width", "height"):
            v = raw.get(k)
            if v and (longest is None or v > longest):
                longest = v

        prof = calculate_profitability(
            selling_price=selling_price,
            cost_price=0,
            weight_kg=float(weight) if weight else None,
            longest_side_cm=float(longest) if longest else None,
            mode=mode,
        )

        results.append(TopProductOut(
            id=product.id,
            asin=product.asin,
            title=product.title,
            brand=product.brand,
            niche=product.niche,
            price=float(product.price),
            buybox_price=float(product.buybox_price) if product.buybox_price else None,
            bsr=product.bsr,
            monthly_sales=product.monthly_sales,
            seller_count=product.seller_count,
            review_count=product.review_count,
            rating=float(product.rating) if product.rating else None,
            amazon_is_seller=product.amazon_is_seller,
            score=float(score),
            max_cost_price=prof["break_even_cost"] * (1 - target_margin / 100),
            total_fees=prof["total_fees"],
            image_url=product.image_url,
        ))

    return results


@router.get("/export-sourcing")
def export_sourcing_csv(
    min_score: float = Query(default=40.0),
    max_bsr: int = Query(default=100000),
    target_margin: float = Query(default=35.0),
    exclude_amazon_seller: bool = Query(default=True),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export top products as CSV for sourcing tools (Tactical Arbitrage, etc.)."""
    from app.services.sourcing_export_service import export_top_products_csv

    csv_content = export_top_products_csv(
        db=db, min_score=min_score, max_bsr=max_bsr,
        target_margin=target_margin, exclude_amazon_seller=exclude_amazon_seller,
        limit=limit,
    )

    import io
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=marcus_sourcing_top_products.csv"},
    )


class ImportCSVResponse(BaseModel):
    file: str
    niche: str
    total_rows: int
    imported: int
    skipped: int
    errors: int
    opportunities_created: int = 0


@router.post("/import-csv", response_model=list[ImportCSVResponse])
def import_helium10_csvs(
    csv_dir: str = Query(default="C:/DEV/SWITAA/CSV"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import all Helium 10 Black Box CSV files from a directory."""
    from app.services.csv_import_service import import_all_csvs

    csv_path = Path(csv_dir)
    if not csv_path.exists():
        raise HTTPException(status_code=400, detail=f"Directory not found: {csv_dir}")

    try:
        results = import_all_csvs(db=db, csv_dir=csv_path, user_id=user.id)
        return results
    except Exception as e:
        logger.exception(f"CSV import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-csv/file", response_model=ImportCSVResponse)
async def import_single_csv_file(
    file: UploadFile = File(...),
    niche: str = Query(...),
    sub_niche: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import a single uploaded Helium 10 CSV file."""
    import tempfile

    from app.services.csv_import_service import import_single_csv

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = import_single_csv(
            db=db, csv_path=tmp_path, niche=niche, sub_niche=sub_niche, user_id=user.id
        )
        return result
    except Exception as e:
        logger.exception(f"CSV upload import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
