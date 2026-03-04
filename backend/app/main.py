import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

app = FastAPI(
    title="Marcus API",
    description="Marcus SaaS - Product Research for Marketplaces",
    version="0.1.0",
    docs_url="/docs" if settings.is_debug else None,
    redoc_url="/redoc" if settings.is_debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes_auth import router as auth_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_discover import router as discover_router
from app.api.routes_export import router as export_router
from app.api.routes_listings import router as listings_router
from app.api.routes_marketplace import router as marketplace_router
from app.api.routes_products import router as products_router
from app.api.routes_scoring import router as scoring_router
from app.api.routes_suppliers import router as suppliers_router

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(discover_router)
app.include_router(scoring_router)
app.include_router(suppliers_router)
app.include_router(listings_router)
app.include_router(marketplace_router)
app.include_router(export_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"message": "Marcus API", "docs": "/docs" if settings.is_debug else "disabled"}
