"""Keepa enrichment service — enriches existing products with Keepa API data.

Adapts batch size to available tokens and waits for refill between batches.
"""
from __future__ import annotations

import asyncio
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
    max_products: int | None = None,
) -> dict[str, Any]:
    """Enrich products with Keepa data, adapting to available tokens.

    Processes only as many ASINs as tokens allow, using small batches
    and waiting for refill between them.
    """
    client = KeepaClient()

    tokens_before = await client.tokens_left()
    if tokens_before < 2:
        return {
            "status": "error",
            "message": f"Keepa tokens too low ({tokens_before}). Wait for refill.",
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
            "enriched": 0,
            "skipped": 0,
            "errors": 0,
            "tokens_before": tokens_before,
            "tokens_after": tokens_before,
            "remaining_to_enrich": 0,
        }

    asin_to_product: dict[str, Product] = {p.asin: p for p in products}
    asins = list(asin_to_product.keys())
    if max_products:
        asins = asins[:max_products]

    batch_size = min(tokens_before - 1, 50)
    batch_size = max(batch_size, 5)

    logger.info(
        "Keepa enrichment: %d products to process, %d tokens available, batch_size=%d",
        len(asins),
        tokens_before,
        batch_size,
    )

    enriched_count = 0
    skipped_count = 0
    error_count = 0
    batches_done = 0

    for i in range(0, len(asins), batch_size):
        batch = asins[i : i + batch_size]

        tokens = await client.tokens_left()
        needed = len(batch) + 1
        if tokens < needed:
            wait_secs = (needed - tokens) * 60 + 10
            logger.info(
                "Waiting %ds for token refill (%d available, %d needed)",
                wait_secs, tokens, needed,
            )
            await asyncio.sleep(wait_secs)
            tokens = await client.tokens_left()
            if tokens < needed:
                logger.warning(
                    "Still not enough tokens after wait (%d < %d), stopping",
                    tokens, needed,
                )
                break

        enriched_list = await client.enrich_batch(
            asins=batch,
            marketplace=marketplace,
            category_multiplier=category_multiplier,
        )

        enriched_map = {e["asin"]: e for e in enriched_list}
        for asin in batch:
            keepa_data = enriched_map.get(asin)
            if not keepa_data:
                skipped_count += 1
                continue
            try:
                product = asin_to_product[asin]
                _merge_keepa_data(product, keepa_data)
                enriched_count += 1
            except Exception:
                logger.exception("Error merging Keepa data for ASIN %s", asin)
                error_count += 1

        db.commit()
        batches_done += 1
        logger.info(
            "Batch %d done: %d/%d enriched so far",
            batches_done, enriched_count, len(asins),
        )

    tokens_after = await client.tokens_left()
    remaining = total - enriched_count - skipped_count - error_count

    logger.info(
        "Keepa enrichment done: %d enriched, %d skipped, %d errors, %d remaining (tokens %d -> %d)",
        enriched_count, skipped_count, error_count, remaining,
        tokens_before, tokens_after,
    )

    return {
        "status": "completed" if remaining == 0 else "partial",
        "total_products": total,
        "batches_processed": batches_done,
        "enriched": enriched_count,
        "skipped": skipped_count,
        "errors": error_count,
        "remaining_to_enrich": remaining,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
    }
