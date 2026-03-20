"""Batch SP-API enrichment for OCTOPIA-imported products.

Fetches catalog data (BSR, sales rank, images) and competitive pricing,
then re-scores opportunities with the fresh data.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product
from app.services.scoring_service import score_product
from app.services.spapi_client import SPAPIClient
from app.services.spapi_enrichment_service import _parse_competitive_pricing, _merge_spapi_data

logger = logging.getLogger("marcus.octopia_enrich")

BSR_TO_SALES_COEFFICIENTS = {
    1: 5000, 100: 2000, 500: 800, 1000: 500,
    5000: 200, 10000: 100, 50000: 30, 100000: 10, 500000: 2,
}


def _estimate_monthly_sales(bsr: int | None) -> int | None:
    """Rough monthly sales estimate from BSR using interpolation."""
    if bsr is None or bsr <= 0:
        return None
    prev_bsr, prev_sales = 1, 5000
    for threshold, sales in sorted(BSR_TO_SALES_COEFFICIENTS.items()):
        if bsr <= threshold:
            ratio = (bsr - prev_bsr) / max(1, threshold - prev_bsr)
            return max(1, int(prev_sales - ratio * (prev_sales - sales)))
        prev_bsr, prev_sales = threshold, sales
    if bsr > 500000:
        return max(1, int(2 * (500000 / bsr)))
    return 1


def _merge_catalog_data(product: Product, catalog: dict[str, Any]) -> None:
    """Merge SP-API catalog item data into product."""
    summaries = catalog.get("summaries", [])
    if summaries:
        s = summaries[0]
        if not product.title or product.title == "":
            product.title = (s.get("itemName") or "")[:500]
        if not product.brand or product.brand == "":
            product.brand = (s.get("brand") or "")[:255]
        if not product.category or product.category == "":
            browse = s.get("browseClassification", {})
            product.category = (browse.get("displayName") or "")[:255]

    images = catalog.get("images", [])
    if images and not product.image_url:
        img_list = images[0].get("images", [])
        if img_list:
            product.image_url = img_list[0].get("link", "")

    sales_ranks = catalog.get("salesRanks", [])
    if sales_ranks:
        for sr_group in sales_ranks:
            ranks = sr_group.get("classificationRanks", []) or sr_group.get("displayGroupRanks", [])
            if ranks:
                best_rank = min(ranks, key=lambda r: r.get("rank", 999999))
                bsr = best_rank.get("rank")
                if bsr and (product.bsr is None or product.bsr == 0):
                    product.bsr = bsr
                    estimated = _estimate_monthly_sales(bsr)
                    if estimated and (product.monthly_sales is None or product.monthly_sales == 0):
                        product.monthly_sales = estimated
                break


def _rescore_opportunities(db: Session, product: Product) -> int:
    """Re-score all opportunities linked to a product. Returns count updated."""
    opps = db.query(Opportunity).filter(Opportunity.product_id == product.id).all()
    updated = 0
    for opp in opps:
        cost_price = float(opp.cost_price) if opp.cost_price else None
        result = score_product(product, cost_price=cost_price)

        selling_price = float(product.price or product.buybox_price or 0)
        if selling_price > 0 and opp.selling_price == 0:
            opp.selling_price = selling_price

        opp.score = result["score"]
        opp.margin_score = result["margin_score"]
        opp.competition_score = result["competition_score"]
        opp.demand_score = result["demand_score"]
        opp.bsr_score = result["bsr_score"]
        opp.margin_abs = result["margin_abs"]
        opp.margin_pct = result["margin_pct"]
        opp.decision = result["decision"]
        updated += 1

    return updated


async def enrich_octopia_products(
    db: Session,
    force: bool = False,
    max_products: int | None = None,
    delay_between: float = 0.6,
) -> dict[str, Any]:
    """Enrich OCTOPIA products with SP-API catalog + pricing data, then re-score."""
    client = SPAPIClient(platform="amazon_fr")

    query = db.query(Product).filter(Product.source == "octopia")
    if not force:
        query = query.filter(
            (Product.bsr.is_(None)) | (Product.bsr == 0)
        )

    products = query.all()
    if max_products:
        products = products[:max_products]

    total = len(products)
    if total == 0:
        return {"status": "completed", "total": 0, "enriched": 0, "errors": 0, "rescored": 0}

    logger.info("OCTOPIA enrichment: %d products to process", total)

    enriched = 0
    errors = 0
    rescored = 0

    for i, product in enumerate(products):
        try:
            catalog = await client.get_catalog_item(product.asin)
            if catalog:
                _merge_catalog_data(product, catalog)
                enriched += 1
            else:
                logger.debug("No catalog data for %s", product.asin)

            pricing = await client.get_competitive_pricing(product.asin)
            if pricing:
                parsed = _parse_competitive_pricing(pricing)
                if parsed:
                    _merge_spapi_data(product, parsed)
                    if parsed.get("buybox_price") and (not product.price or float(product.price) == 0):
                        product.price = parsed["buybox_price"]

            rescored += _rescore_opportunities(db, product)

        except Exception:
            logger.exception("Enrichment error for ASIN %s", product.asin)
            errors += 1

        if (i + 1) % 25 == 0:
            db.commit()
            logger.info("OCTOPIA enrichment progress: %d/%d (enriched=%d, errors=%d)", i + 1, total, enriched, errors)

        await asyncio.sleep(delay_between)

    db.commit()

    remaining = db.query(Product).filter(
        Product.source == "octopia",
        (Product.bsr.is_(None)) | (Product.bsr == 0),
    ).count()

    logger.info(
        "OCTOPIA enrichment done: %d/%d enriched, %d errors, %d rescored, %d remaining",
        enriched, total, errors, rescored, remaining,
    )

    return {
        "status": "completed",
        "total": total,
        "enriched": enriched,
        "errors": errors,
        "rescored": rescored,
        "remaining": remaining,
    }
