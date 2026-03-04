"""Campaign API routes - create, list, run search campaigns."""
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.search_campaign import SearchCampaign, SearchResult
from app.services.research_pipeline import NICHE_KEYWORDS, run_campaign

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


# --- Request/Response models ---


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    niche: str = Field(..., max_length=50)
    sub_niche: str = Field(default="", max_length=100)
    keywords: list[str] = Field(default_factory=list)
    marketplace: str = Field(default="amazon_fr", max_length=50)
    filters: dict[str, Any] = Field(default_factory=dict)
    target_count: int = Field(default=50, ge=1, le=500)


class CampaignOut(BaseModel):
    id: UUID
    name: str
    niche: str
    sub_niche: str
    keywords: list[str]
    marketplace: str
    status: str
    phase: str
    progress_pct: int
    target_count: int
    found_count: int
    filters: Optional[dict[str, Any]] = None
    error_message: str = ""
    user_id: Optional[UUID] = None
    created_at: Any
    completed_at: Optional[Any] = None

    model_config = {"from_attributes": True}


class QuickStartOut(BaseModel):
    campaign_ids: list[UUID]


class CampaignResultOut(BaseModel):
    id: UUID
    asin: str
    title: str
    brand: str
    category: str
    marketplace: str
    price: float
    bsr: Optional[int] = None
    monthly_sales: Optional[int] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    seller_count: Optional[int] = None
    image_url: str = ""
    amazon_is_seller: Optional[bool] = None
    score: Optional[float] = None
    decision: Optional[str] = None
    keyword: str = ""

    model_config = {"from_attributes": True}


# --- Endpoints ---


@router.post("/", response_model=CampaignOut)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new search campaign."""
    campaign = SearchCampaign(
        name=body.name,
        niche=body.niche,
        sub_niche=body.sub_niche,
        keywords=body.keywords,
        marketplace=body.marketplace,
        filters=body.filters if body.filters else None,
        target_count=body.target_count,
        user_id=user.id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/quick-start", response_model=QuickStartOut)
def quick_start_campaigns(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create and launch all 8 sub-niches at once using NICHE_KEYWORDS."""
    campaign_ids: list[UUID] = []
    for key, config in NICHE_KEYWORDS.items():
        campaign = SearchCampaign(
            name=f"{config['niche']} - {config['sub_niche']}",
            niche=config["niche"],
            sub_niche=config["sub_niche"],
            keywords=config["keywords"],
            marketplace="amazon_fr",
            target_count=50,
            user_id=user.id,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        campaign_ids.append(campaign.id)
        background_tasks.add_task(run_campaign, str(campaign.id), str(user.id))

    return QuickStartOut(campaign_ids=campaign_ids)


@router.get("/", response_model=list[CampaignOut])
def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, error)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all campaigns, optionally filtered by status."""
    q = db.query(SearchCampaign)
    if status:
        q = q.filter(SearchCampaign.status == status)
    return q.order_by(SearchCampaign.created_at.desc()).all()


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get campaign detail with status, phase, progress."""
    campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/results", response_model=list[CampaignResultOut])
def get_campaign_results(
    campaign_id: UUID,
    min_score: Optional[float] = Query(None, description="Minimum opportunity score"),
    min_price: Optional[float] = Query(None, description="Minimum product price"),
    max_sellers: Optional[int] = Query(None, description="Maximum seller count"),
    amazon_is_seller: Optional[bool] = Query(None, description="Filter by Amazon as seller"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get products found by this campaign (SearchResult + Product + Opportunity), with filters."""
    campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    q = (
        db.query(Product, SearchResult.keyword, Opportunity.score, Opportunity.decision)
        .join(SearchResult, SearchResult.product_id == Product.id)
        .outerjoin(Opportunity, (Opportunity.product_id == Product.id) & (Opportunity.campaign_id == campaign_id))
        .filter(SearchResult.campaign_id == campaign_id)
    )

    if min_score is not None:
        q = q.filter(Opportunity.score >= min_score)
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_sellers is not None:
        q = q.filter(Product.seller_count <= max_sellers)
    if amazon_is_seller is not None:
        q = q.filter(Product.amazon_is_seller == amazon_is_seller)

    rows = q.all()
    return [
        CampaignResultOut(
            id=p.id,
            asin=p.asin,
            title=p.title or "",
            brand=p.brand or "",
            category=p.category or "",
            marketplace=p.marketplace or "",
            price=float(p.price or 0),
            bsr=p.bsr,
            monthly_sales=p.monthly_sales,
            review_count=p.review_count,
            rating=float(p.rating) if p.rating else None,
            seller_count=p.seller_count,
            image_url=p.image_url or "",
            amazon_is_seller=p.amazon_is_seller,
            score=float(score) if score is not None else None,
            decision=decision,
            keyword=keyword or "",
        )
        for p, keyword, score, decision in rows
    ]


@router.post("/{campaign_id}/run")
def run_campaign_endpoint(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Launch a campaign (background task)."""
    campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="Campaign is already running")

    background_tasks.add_task(run_campaign, str(campaign_id), str(user.id))
    return {"status": "started", "campaign_id": str(campaign_id), "message": "Campaign launched in background"}


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a campaign."""
    campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db.delete(campaign)
    db.commit()
