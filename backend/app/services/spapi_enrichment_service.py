"""SP-API enrichment service — free BuyBox + competitive pricing data."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.spapi_client import SPAPIClient

logger = logging.getLogger("marcus.spapi_enrichment")


def _parse_competitive_pricing(data: dict[str, Any]) -> dict[str, Any]:
    """Extract BuyBox, lowest FBA/FBM prices from SP-API competitive pricing response."""
    result: dict[str, Any] = {}
    payload = data.get("payload") or data
    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    product_data = payload.get("Product", payload)
    comp_prices = product_data.get("CompetitivePricing", {})

    prices = comp_prices.get("CompetitivePrices", [])
    for cp in prices:
        cond = cp.get("condition", "")
        belongs = cp.get("belongsToRequester", False)
        price_info = cp.get("Price", {})
        landed = price_info.get("LandedPrice", {})
        listing = price_info.get("ListingPrice", {})
        amount = landed.get("Amount") or listing.get("Amount")
        if amount is not None:
            amount = float(amount)

        comp_type = cp.get("CompetitivePriceId", "")
        if comp_type == "1":
            result["buybox_price"] = amount
            result["buybox_is_mine"] = belongs
        elif comp_type == "2":
            result["lowest_new_price"] = amount

    offers = comp_prices.get("NumberOfOfferListings", [])
    for offer in offers:
        cond = offer.get("condition", "")
        ff = offer.get("fulfillmentChannel", "")
        count = int(offer.get("Count", 0))
        if cond == "New" and ff == "Amazon":
            result["fba_offer_count"] = count
        elif cond == "New" and ff == "Merchant":
            result["fbm_offer_count"] = count

    trade_in = product_data.get("SalesRankings", [])
    for sr in trade_in:
        if sr.get("ProductCategoryId"):
            result.setdefault("bsr_from_spapi", sr.get("Rank"))
            break

    return result


def _merge_spapi_data(product: Product, spapi_data: dict[str, Any]) -> None:
    """Merge SP-API competitive pricing into product."""
    if "buybox_price" in spapi_data and spapi_data["buybox_price"]:
        product.buybox_price = spapi_data["buybox_price"]

    fba_count = spapi_data.get("fba_offer_count", 0)
    fbm_count = spapi_data.get("fbm_offer_count", 0)

    if product.seller_count is None or product.seller_count == 0:
        total = fba_count + fbm_count
        if total > 0:
            product.seller_count = total

    existing_raw = product.raw_data or {}
    existing_raw["spapi"] = spapi_data
    product.raw_data = existing_raw


async def run_spapi_enrichment(
    db: Session,
    source_filter: str = "helium10_blackbox",
    force: bool = False,
    max_products: int | None = None,
    delay_between: float = 0.5,
) -> dict[str, Any]:
    """Enrich products with free SP-API competitive pricing data.

    Rate-limited to avoid SP-API throttling (default 0.5s between calls).
    """
    settings_module = __import__("app.core.config", fromlist=["get_settings"])
    settings = settings_module.get_settings()

    if not settings.SPAPI_LWA_CLIENT_ID or not settings.SPAPI_LWA_REFRESH_TOKEN:
        return {
            "status": "error",
            "message": "SP-API credentials not configured. Set SPAPI_LWA_CLIENT_ID, SPAPI_LWA_CLIENT_SECRET, and SPAPI_LWA_REFRESH_TOKEN.",
            "enriched": 0,
        }

    client = SPAPIClient()

    query = db.query(Product).filter(Product.source == source_filter)
    if not force:
        query = query.filter(Product.buybox_price.is_(None))
    products = query.all()

    if max_products:
        products = products[:max_products]

    total = len(products)
    if total == 0:
        return {"status": "completed", "total": 0, "enriched": 0, "errors": 0, "remaining": 0}

    logger.info("SP-API enrichment: %d products to process", total)

    enriched = 0
    errors = 0

    for i, product in enumerate(products):
        try:
            data = await client.get_competitive_pricing(product.asin)
            if data:
                parsed = _parse_competitive_pricing(data)
                if parsed:
                    _merge_spapi_data(product, parsed)
                    enriched += 1
                else:
                    errors += 1
            else:
                errors += 1
        except Exception:
            logger.exception("SP-API error for ASIN %s", product.asin)
            errors += 1

        if (i + 1) % 50 == 0:
            db.commit()
            logger.info("SP-API progress: %d/%d enriched", enriched, total)

        await asyncio.sleep(delay_between)

    db.commit()

    all_remaining = db.query(Product).filter(
        Product.source == source_filter, Product.buybox_price.is_(None)
    ).count()

    logger.info("SP-API enrichment done: %d enriched, %d errors, %d remaining", enriched, errors, all_remaining)

    return {
        "status": "completed",
        "total": total,
        "enriched": enriched,
        "errors": errors,
        "remaining": all_remaining,
    }
