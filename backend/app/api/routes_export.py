from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/opportunities")
def export_opportunities(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    min_score: float = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.export_service import export_opportunities_data

    buffer, content_type, filename = export_opportunities_data(db, format, min_score)
    return StreamingResponse(
        buffer,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
