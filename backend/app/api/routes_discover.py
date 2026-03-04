from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/discover", tags=["discover"])


class DiscoverRequest(BaseModel):
    marketplace: str = "amazon_fr"
    source: str = "keepa"  # keepa, spapi, helium10
    category: str = ""
    min_price: float = 10
    max_price: float = 100
    min_sales: int = 100
    max_reviews: int = 200


class DiscoverResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post("/run", response_model=DiscoverResponse)
async def run_discover(
    req: DiscoverRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import uuid

    job_id = str(uuid.uuid4())

    from app.services.discover_service import run_discovery

    background_tasks.add_task(run_discovery, job_id, req, str(user.id))

    return DiscoverResponse(
        job_id=job_id,
        status="started",
        message=f"Discovery started on {req.marketplace} via {req.source}",
    )
