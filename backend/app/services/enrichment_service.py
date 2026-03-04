"""Keepa enrichment service — enriches existing products with Keepa API data."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.keepa_client import KeepaClient

logger = logging.getLogger("marcus.enrichment")

KEEPA_EXCLUSIVE_FIELDS = {
    "amazon_is_seller",
    "buybox_seller",
    "buybox_price",
    "price_stability",
}

KEEPA_FALLBACK_FIELDS = {
    "bsr",
    "monthly_sales",
    "review_count",
    "rating",
    "seller_count",
    "image_url",
}


def _merge_keepa_data(product: Product, keepa_data: dict[str, Any]) -> None:
    """Merge Keepa enrichment data into existing product.
    BuyBox / price_stability always overwrite.
    Other numeric fields only fill blanks so H10 values are preserved.
    """
    for field in KEEPA_EXCLUSIVE_FIELDS:
        value = keepa_data.get(field)
        if value is not None:
            setattr(product, field, value)

    for field in KEEPA_FALLBACK_FIELDS:
        current = getattr(product, field, None)
        value = keepa_data.get(field)
        if (current is None or current in (0, "")) and value:
            setattr(product, field, value)

    existing_raw = product.raw_data or {}
    existing_raw["keepa"] = keepa_data.get("raw_data", {})
    product.raw_data = existing_raw


async def run_keepa_enrichment(
    db: Session,
    source_filter: str = "helium10_blackbox",
    marketplace: str = "amazon_fr",
    category_multiplier: float = 1.5,
    force: bool = False,
) -> dict[str, Any]:
    """Enrich products matching *source_filter* with Keepa data.

    By default, only products missing buybox / price_stability data are
    processed.  Set *force=True* to re-enrich everything.
    """
    client = KeepaClient()

    tokens_before = await client.tokens_left()
    if tokens_before < 10:
        return {
            "status": "error",
            "message": "Insufficient Keepa API tokens",
            "tokens_left": tokens_before,
        }

    query = db.query(Product).filter(Product.source == source_filter)
    if not force:
        query = query.filter(
            (Product.buybox_seller.is_(None)) | (Product.price_stability.is_(None))
        )
    products = query.all()

    total = len(products)
    if total == 0:
        return {
            "status": "completed",
            "total_products": 0,
            "batches_processed": 0,
            "enriched": 0,
            "skipped": 0,
            "errors": 0,
            "tokens_before": tokens_before,
            "tokens_after": tokens_before,
        }

    asin_to_product: dict[str, Product] = {p.asin: p for p in products}
    asins = list(asin_to_product.keys())

    logger.info(
        "Starting Keepa enrichment: %d products, ~%d batches",
        len(asins),
        (len(asins) + 99) // 100,
    )

    enriched_list = await client.enrich_batch(
        asins=asins,
        marketplace=marketplace,
        category_multiplier=category_multiplier,
    )

    enriched_map: dict[str, dict[str, Any]] = {e["asin"]: e for e in enriched_list}
    enriched_count = 0
    skipped_count = 0
    error_count = 0

    for asin, product in asin_to_product.items():
        keepa_data = enriched_map.get(asin)
        if not keepa_data:
            skipped_count += 1
            continue
        try:
            _merge_keepa_data(product, keepa_data)
            enriched_count += 1
        except Exception:
            logger.exception("Error merging Keepa data for ASIN %s", asin)
            error_count += 1

    db.commit()
    tokens_after = await client.tokens_left()

    logger.info(
        "Keepa enrichment done: %d enriched, %d skipped, %d errors (tokens %d -> %d)",
        enriched_count,
        skipped_count,
        error_count,
        tokens_before,
        tokens_after,
    )

    return {
        "status": "completed",
        "total_products": total,
        "batches_processed": (len(asins) + 99) // 100,
        "enriched": enriched_count,
        "skipped": skipped_count,
        "errors": error_count,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
    }
