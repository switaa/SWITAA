"""Monitor Amazon prices and detect margin erosion for active opportunities."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product, ProductHistory

logger = logging.getLogger("marcus.price_monitor")

MARGIN_ALERT_THRESHOLD_PCT = 15.0
PRICE_DROP_THRESHOLD_PCT = 10.0


async def run_price_check(
    db: Session,
    margin_threshold: float = MARGIN_ALERT_THRESHOLD_PCT,
    price_drop_threshold: float = PRICE_DROP_THRESHOLD_PCT,
) -> dict[str, Any]:
    """Check prices via SP-API for products with active opportunities.

    Returns alerts for products where:
    - Amazon price dropped enough to erode margin below threshold
    - Significant price change detected vs last recorded price
    """
    from app.services.spapi_client import SPAPIClient

    spapi = SPAPIClient()

    active_opps = (
        db.query(Opportunity)
        .join(Product, Opportunity.product_id == Product.id)
        .filter(Opportunity.decision.in_(["A_launch", "B_review"]))
        .filter(Product.status != "archived")
        .order_by(Opportunity.score.desc())
        .limit(200)
        .all()
    )

    stats: dict[str, Any] = {
        "products_checked": 0,
        "prices_updated": 0,
        "alerts_generated": 0,
        "errors": 0,
        "alerts": [],
    }

    for opp in active_opps:
        product = opp.product
        if not product:
            continue

        try:
            pricing_data = await spapi.get_competitive_pricing(product.asin)
            if not pricing_data:
                stats["errors"] += 1
                continue

            stats["products_checked"] += 1

            new_price = _extract_buybox_price(pricing_data)
            if new_price is None or new_price <= 0:
                continue

            old_price = float(product.buybox_price or product.price or 0)

            history = ProductHistory(
                product_id=product.id,
                price=new_price,
                bsr=product.bsr,
                seller_count=product.seller_count,
                source="spapi_price_monitor",
            )
            db.add(history)

            if old_price > 0 and new_price != old_price:
                product.buybox_price = new_price
                product.price = new_price
                stats["prices_updated"] += 1

                pct_change = ((new_price - old_price) / old_price) * 100

                if pct_change < -price_drop_threshold:
                    cost = float(opp.cost_price or 0)
                    fees = new_price * 0.15
                    new_margin = new_price - fees - cost
                    new_margin_pct = (new_margin / new_price * 100) if new_price > 0 else 0

                    alert_data = {
                        "type": "price_drop",
                        "asin": product.asin,
                        "product_id": str(product.id),
                        "old_price": old_price,
                        "new_price": new_price,
                        "change_pct": round(pct_change, 1),
                        "new_margin_pct": round(new_margin_pct, 1),
                        "severity": "critical" if new_margin_pct < 0 else "warning",
                    }
                    stats["alerts"].append(alert_data)
                    stats["alerts_generated"] += 1

                    if new_margin_pct < 0:
                        opp.decision = "C_drop"
                        opp.notes = f"{opp.notes} | PRICE DROP: {old_price:.2f}→{new_price:.2f} ({pct_change:.1f}%)"

        except Exception as e:
            stats["errors"] += 1
            logger.warning("Price check error for %s: %s", product.asin, e)

    db.commit()
    logger.info(
        "Price check: %d checked, %d updated, %d alerts",
        stats["products_checked"],
        stats["prices_updated"],
        stats["alerts_generated"],
    )
    return stats


def _extract_buybox_price(pricing_data: dict) -> float | None:
    try:
        payload = pricing_data.get("payload", [])
        if not payload:
            return None
        item = payload[0] if isinstance(payload, list) else payload
        comp = item.get("Product", {}).get("CompetitivePricing", {})
        prices = comp.get("CompetitivePrices", [])
        for p in prices:
            if p.get("CompetitivePriceId") == "1":
                amount = p.get("Price", {}).get("ListingPrice", {}).get("Amount")
                if amount is not None:
                    return float(amount)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return None
