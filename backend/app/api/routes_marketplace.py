from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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
    id: str
    platform: str
    seller_id: str
    is_active: bool

    model_config = {"from_attributes": True}


class PushRequest(BaseModel):
    listing_id: str
    marketplace_account_id: str


class PushLogOut(BaseModel):
    id: str
    listing_id: str
    status: str
    error_message: str

    model_config = {"from_attributes": True}


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
