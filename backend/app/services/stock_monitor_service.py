"""Monitor source supplier stock availability for active opportunities."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.supplier import SupplierProduct

logger = logging.getLogger("marcus.stock_monitor")


async def run_stock_check(
    db: Session,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Check source URLs for stock availability.

    For each active opportunity with a linked SupplierProduct,
    fetches the source URL and checks for out-of-stock indicators.
    """
    active_opps = (
        db.query(Opportunity)
        .filter(Opportunity.supplier_product_id.isnot(None))
        .filter(Opportunity.decision.in_(["A_launch", "B_review"]))
        .order_by(Opportunity.score.desc())
        .limit(200)
        .all()
    )

    stats: dict[str, Any] = {
        "products_checked": 0,
        "out_of_stock": 0,
        "back_in_stock": 0,
        "errors": 0,
        "alerts": [],
    }

    OOS_INDICATORS = [
        "rupture de stock",
        "indisponible",
        "out of stock",
        "produit non disponible",
        "article non disponible",
        "ce produit n'est plus",
        "épuisé",
        "plus disponible",
    ]

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for opp in active_opps:
            sp = db.query(SupplierProduct).filter(
                SupplierProduct.id == opp.supplier_product_id
            ).first()
            if not sp:
                continue

            product = opp.product
            raw = product.raw_data or {} if product else {}
            source_url = raw.get("source_url", "")
            if not source_url:
                continue

            try:
                resp = await client.get(source_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MarcusBot/1.0)"
                })
                stats["products_checked"] += 1

                if resp.status_code == 404:
                    was_in_stock = sp.stock > 0
                    sp.stock = 0
                    if was_in_stock:
                        stats["out_of_stock"] += 1
                        stats["alerts"].append({
                            "type": "out_of_stock",
                            "asin": sp.asin,
                            "source_url": source_url,
                            "reason": "404 page not found",
                            "severity": "warning",
                        })
                    continue

                if resp.status_code != 200:
                    stats["errors"] += 1
                    continue

                page_text = resp.text.lower()
                is_oos = any(indicator in page_text for indicator in OOS_INDICATORS)

                was_in_stock = sp.stock > 0

                if is_oos and was_in_stock:
                    sp.stock = 0
                    stats["out_of_stock"] += 1
                    stats["alerts"].append({
                        "type": "out_of_stock",
                        "asin": sp.asin,
                        "source_url": source_url,
                        "reason": "OOS indicator found on page",
                        "severity": "warning",
                    })
                elif not is_oos and not was_in_stock:
                    sp.stock = 1
                    stats["back_in_stock"] += 1
                    stats["alerts"].append({
                        "type": "back_in_stock",
                        "asin": sp.asin,
                        "source_url": source_url,
                        "severity": "info",
                    })

            except Exception as e:
                stats["errors"] += 1
                logger.debug("Stock check error for %s: %s", source_url[:60], e)

    db.commit()
    logger.info(
        "Stock check: %d checked, %d OOS, %d back in stock, %d errors",
        stats["products_checked"],
        stats["out_of_stock"],
        stats["back_in_stock"],
        stats["errors"],
    )
    return stats
