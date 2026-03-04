from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
    id: str
    product_id: str
    marketplace: str
    title: str
    bullets: list | None
    description: str
    status: str

    model_config = {"from_attributes": True}


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
