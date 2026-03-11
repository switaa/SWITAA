from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.listing import Listing
from app.models.user import User

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])


class ListingCreate(BaseModel):
    product_id: str
    marketplace: str = "amazon_fr"
    title: str
    bullets: list[str] | None = None
    description: str = ""
    search_terms: str = ""
    brand_name: str = ""
    strategy: str = "clone_best"


class ListingOut(BaseModel):
    id: UUID
    product_id: UUID
    marketplace: str
    title: str
    bullets: list | None
    description: str
    search_terms: str
    brand_name: str
    strategy: str
    status: str
    sku: str

    model_config = {"from_attributes": True}


class GenerateBatchRequest(BaseModel):
    strategy: str = "clone_best"
    min_score: float = 70.0
    decision: str | None = "A_launch"
    limit: int = 50


class GenerateBatchResponse(BaseModel):
    total_opportunities: int
    listings_created: int
    listings_updated: int
    errors: int


@router.get("/", response_model=list[ListingOut])
def list_listings(
    status: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Listing)
    if status:
        q = q.filter(Listing.status == status)
    return q.order_by(Listing.updated_at.desc()).limit(limit).all()


@router.post("/", response_model=ListingOut, status_code=201)
def create_listing(
    req: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    listing = Listing(**req.model_dump(), user_id=user.id)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.put("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: UUID,
    req: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    for k, v in req.model_dump().items():
        setattr(listing, k, v)
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/{listing_id}/approve", response_model=ListingOut)
def approve_listing(
    listing_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "approved"
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/generate/{product_id}", response_model=ListingOut)
async def generate_listing_for_product(
    product_id: UUID,
    strategy: str = Query("clone_best"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a listing for a single product using the specified strategy."""
    from app.services.listing_generator_service import generate_single_listing

    try:
        listing = await generate_single_listing(
            db=db,
            product_id=str(product_id),
            user_id=str(user.id),
            strategy=strategy,
        )
        return listing
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/generate-batch", response_model=GenerateBatchResponse)
async def generate_listings_batch(
    req: GenerateBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Batch-generate listings for top-scored opportunities."""
    from app.services.listing_generator_service import generate_batch_listings

    stats = await generate_batch_listings(
        db=db,
        user_id=str(user.id),
        strategy=req.strategy,
        min_score=req.min_score,
        decision=req.decision,
        limit=req.limit,
    )
    return GenerateBatchResponse(**stats)
