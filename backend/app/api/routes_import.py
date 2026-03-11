"""Routes for importing data from various sources (TA, H10, CSV)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/import", tags=["import"])

_import_jobs: dict[str, dict[str, Any]] = {}


class ImportResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ImportStatusResponse(BaseModel):
    job_id: str
    status: str
    stats: dict[str, Any] | None = None
    error: str | None = None


def _run_ta_import_background(
    job_id: str,
    csv_content: str,
    user_id: str,
    min_match_quality: int,
    min_roi: float,
    min_profit: float,
):
    from app.services.ta_import_service import import_ta_csv

    db = SessionLocal()
    try:
        _import_jobs[job_id]["status"] = "running"
        stats = import_ta_csv(
            db=db,
            csv_content=csv_content,
            user_id=uuid.UUID(user_id),
            min_match_quality=min_match_quality,
            min_roi=min_roi,
            min_profit=min_profit,
        )
        _import_jobs[job_id]["status"] = "completed"
        _import_jobs[job_id]["stats"] = stats
    except Exception as e:
        _import_jobs[job_id]["status"] = "error"
        _import_jobs[job_id]["error"] = str(e)
    finally:
        db.close()


@router.post("/ta-csv", response_model=ImportResponse)
async def import_ta_csv_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    min_match_quality: int = Query(80, ge=0, le=100),
    min_roi: float = Query(0, ge=0),
    min_profit: float = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    """Import a Tactical Arbitrage Product Search CSV file.

    Processes the CSV in background: creates Products, SupplierProducts,
    and scored Opportunities.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    csv_text = content.decode("utf-8-sig")

    job_id = str(uuid.uuid4())
    _import_jobs[job_id] = {"status": "queued", "stats": None, "error": None}

    background_tasks.add_task(
        _run_ta_import_background,
        job_id,
        csv_text,
        str(user.id),
        min_match_quality,
        min_roi,
        min_profit,
    )

    return ImportResponse(
        job_id=job_id,
        status="queued",
        message=f"TA CSV import queued ({len(csv_text)} bytes)",
    )


@router.get("/status/{job_id}", response_model=ImportStatusResponse)
def get_import_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Check the status of an import job."""
    job = _import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ImportStatusResponse(
        job_id=job_id,
        status=job["status"],
        stats=job.get("stats"),
        error=job.get("error"),
    )
