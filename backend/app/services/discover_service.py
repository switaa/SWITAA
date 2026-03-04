"""Discovery orchestrator - runs product searches via Keepa, SP-API, or Helium 10."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.product import Product

logger = logging.getLogger("marcus.discover")


async def run_discovery(job_id: str, request, user_id: str):
    logger.info(f"[{job_id}] Starting discovery: {request.source} on {request.marketplace}")
    db = SessionLocal()

    try:
        products_data = []

        if request.source == "keepa":
            from app.services.keepa_client import KeepaClient

            keepa = KeepaClient()
            tokens = await keepa.tokens_left()
            logger.info(f"Keepa tokens left: {tokens}")
            # Category search would go here with actual category IDs

        elif request.source == "spapi":
            from app.services.spapi_client import SPAPIClient

            spapi = SPAPIClient()
            # SP-API catalog search implementation

        elif request.source == "helium10":
            from app.services.helium10_service import Helium10Service

            h10 = Helium10Service()
            products_data = await h10.search_by_keyword(
                keyword=request.keyword or request.category or "product",
                filters={
                    "marketplace": request.marketplace,
                    "min_price": request.min_price,
                    "max_price": request.max_price,
                    "max_reviews": request.max_reviews,
                },
            )
            await h10.close()

        saved = 0
        for p_data in products_data:
            existing = db.query(Product).filter(Product.asin == p_data["asin"]).first()
            if existing:
                for k, v in p_data.items():
                    if k not in ("asin", "raw_data") and v:
                        setattr(existing, k, v)
            else:
                product = Product(**{k: v for k, v in p_data.items() if k != "raw_data"}, user_id=user_id)
                db.add(product)
            saved += 1

        db.commit()
        logger.info(f"[{job_id}] Discovery complete: {saved} products saved")

    except Exception as e:
        logger.error(f"[{job_id}] Discovery error: {e}")
        db.rollback()
    finally:
        db.close()
