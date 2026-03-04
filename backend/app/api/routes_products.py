import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
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

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ProductOut])
def list_products(
    marketplace: str = Query(None),
    category: str = Query(None),
    status: str = Query(None),
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
