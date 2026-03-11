"""Marketplace accounts, push operations, and push log endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.listing import Listing
from app.models.marketplace import MarketplaceAccount, PushLog
from app.models.user import User

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


class AccountCreate(BaseModel):
    platform: str
    seller_id: str = ""
    credentials: dict | None = None


class AccountOut(BaseModel):
    id: UUID
    platform: str
    seller_id: str
    is_active: bool

    model_config = {"from_attributes": True}


class PushRequest(BaseModel):
    listing_id: str
    marketplace_account_id: str


class PushBatchRequest(BaseModel):
    listing_ids: list[str]
    marketplace_account_id: str


class PushLogOut(BaseModel):
    id: UUID
    listing_id: UUID
    marketplace_account_id: UUID
    status: str
    error_message: str
    pushed_at: str | None = None

    model_config = {"from_attributes": True}


class PushBatchResponse(BaseModel):
    total: int
    queued: int
    skipped: int
    errors: int


# --- Account endpoints ---


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(MarketplaceAccount).filter(MarketplaceAccount.user_id == user.id).all()


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(
    req: AccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = MarketplaceAccount(**req.model_dump(), user_id=user.id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/accounts/{account_id}/toggle", response_model=AccountOut)
def toggle_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle a marketplace account on/off."""
    account = db.query(MarketplaceAccount).filter(
        MarketplaceAccount.id == account_id,
        MarketplaceAccount.user_id == user.id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Marketplace account not found")
    account.is_active = not account.is_active
    db.commit()
    db.refresh(account)
    return account


# --- Push endpoints ---


@router.post("/push", response_model=PushLogOut)
async def push_listing(
    req: PushRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    account = db.query(MarketplaceAccount).filter(
        MarketplaceAccount.id == req.marketplace_account_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Marketplace account not found")
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Marketplace account is disabled")

    if not listing.sku:
        from app.models.product import Product
        product = db.query(Product).filter(Product.id == listing.product_id).first()
        listing.sku = f"MARCUS-{product.asin}" if product else f"MARCUS-{listing.id}"
        db.commit()

    log = PushLog(
        listing_id=listing.id,
        marketplace_account_id=account.id,
        status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    from app.services.marketplace_push_service import push_to_marketplace

    background_tasks.add_task(push_to_marketplace, str(log.id))
    return log


@router.post("/push-batch", response_model=PushBatchResponse)
async def push_batch_endpoint(
    req: PushBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Push multiple listings to a marketplace account in one request."""
    from app.services.marketplace_push_service import push_batch

    try:
        stats = await push_batch(
            db=db,
            listing_ids=req.listing_ids,
            marketplace_account_id=req.marketplace_account_id,
        )
        return PushBatchResponse(
            total=stats["total"],
            queued=stats["queued"],
            skipped=stats["skipped"],
            errors=stats["errors"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Push logs ---


@router.get("/push-logs", response_model=list[PushLogOut])
def list_push_logs(
    status: str = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List push logs with optional status filter."""
    q = db.query(PushLog)
    if status:
        q = q.filter(PushLog.status == status)
    return q.order_by(PushLog.pushed_at.desc()).offset(offset).limit(limit).all()
