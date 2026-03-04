from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.supplier import Supplier
from app.models.user import User

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


class SupplierCreate(BaseModel):
    name: str
    access_type: str = "FTP"
    host: str
    port: int = 21
    username: str = ""
    password: str = ""
    root_path: str = ""
    csv_path: str = ""
    encoding: str = "utf-8"
    delimiter: str = ";"
    mapping_json: dict | None = None


class SupplierOut(BaseModel):
    id: str
    name: str
    access_type: str
    host: str
    active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Supplier).filter(Supplier.active.is_(True)).all()


@router.post("/", response_model=SupplierOut, status_code=201)
def create_supplier(
    req: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier = Supplier(**req.model_dump(), user_id=user.id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.post("/{supplier_id}/import")
async def import_catalog(
    supplier_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    from app.services.supplier_feed_service import import_supplier_catalog

    background_tasks.add_task(import_supplier_catalog, str(supplier_id))
    return {"status": "import_started", "supplier": supplier.name}
