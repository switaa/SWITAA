"""Push listings to marketplaces (Amazon, Fnac, Rue du Commerce, CDiscount)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.listing import Listing
from app.models.marketplace import MarketplaceAccount, PushLog
from app.models.product import Product

logger = logging.getLogger("marcus.marketplace_push")


async def push_to_marketplace(push_log_id: str):
    """Push a single listing to its target marketplace."""
    db = SessionLocal()
    try:
        log = db.query(PushLog).filter(PushLog.id == push_log_id).first()
        if not log:
            return

        listing = db.query(Listing).filter(Listing.id == log.listing_id).first()
        account = db.query(MarketplaceAccount).filter(
            MarketplaceAccount.id == log.marketplace_account_id
        ).first()

        if not listing or not account:
            log.status = "error"
            log.error_message = "Listing or account not found"
            db.commit()
            return

        if not account.is_active:
            log.status = "error"
            log.error_message = "Marketplace account is disabled"
            db.commit()
            return

        product = db.query(Product).filter(Product.id == listing.product_id).first()

        listing.marketplace_status = "pushing"
        db.commit()

        logger.info("Pushing listing %s to %s", listing.id, account.platform)

        if account.platform.startswith("amazon"):
            result = await _push_amazon(listing, product, account)
        elif account.platform == "fnac":
            result = await _push_fnac(listing, product, account)
        elif account.platform in ("rdc", "cdiscount"):
            result = await _push_cdiscount(listing, product, account)
        else:
            result = {"success": False, "error": f"Unsupported platform: {account.platform}"}

        if result.get("success"):
            log.status = "success"
            log.response_data = result
            listing.status = "published"
            listing.marketplace_status = "live"
            listing.last_push_at = datetime.now(timezone.utc)
        else:
            log.status = "error"
            log.error_message = result.get("error", "Unknown error")
            log.response_data = result
            listing.marketplace_status = "error"

        db.commit()
        logger.info("Push result for %s: %s", listing.id, log.status)

    except Exception as e:
        logger.error("Push error: %s", e)
        try:
            if log:
                log.status = "error"
                log.error_message = str(e)
            if listing:
                listing.marketplace_status = "error"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def push_batch(
    db: Session,
    listing_ids: list[str],
    marketplace_account_id: str,
) -> dict[str, Any]:
    """Push multiple listings to a marketplace. Returns summary stats."""
    account = db.query(MarketplaceAccount).filter(
        MarketplaceAccount.id == marketplace_account_id
    ).first()
    if not account:
        raise ValueError("Marketplace account not found")
    if not account.is_active:
        raise ValueError("Marketplace account is disabled")

    stats = {"total": len(listing_ids), "queued": 0, "skipped": 0, "errors": 0}
    push_log_ids: list[str] = []

    for lid in listing_ids:
        listing = db.query(Listing).filter(Listing.id == lid).first()
        if not listing:
            stats["skipped"] += 1
            continue
        if listing.status not in ("approved", "auto_generated", "draft"):
            stats["skipped"] += 1
            continue

        if not listing.sku:
            product = db.query(Product).filter(Product.id == listing.product_id).first()
            listing.sku = f"MARCUS-{product.asin}" if product else f"MARCUS-{listing.id}"

        log_entry = PushLog(
            listing_id=listing.id,
            marketplace_account_id=account.id,
            status="pending",
        )
        db.add(log_entry)
        db.flush()
        push_log_ids.append(str(log_entry.id))
        stats["queued"] += 1

    db.commit()

    for plid in push_log_ids:
        try:
            await push_to_marketplace(plid)
        except Exception as e:
            stats["errors"] += 1
            logger.error("Batch push error for log %s: %s", plid, e)

    stats["push_log_ids"] = push_log_ids
    return stats


async def _push_amazon(
    listing: Listing, product: Product, account: MarketplaceAccount
) -> dict[str, Any]:
    from app.services.spapi_client import SPAPIClient

    spapi = SPAPIClient(platform=account.platform)

    creds = account.credentials or {}
    if creds.get("refresh_token"):
        spapi.refresh_token = creds["refresh_token"]
    if creds.get("client_id"):
        spapi.client_id = creds["client_id"]
    if creds.get("client_secret"):
        spapi.client_secret = creds["client_secret"]
    if account.seller_id:
        spapi.seller_id = account.seller_id

    sku = listing.sku or (f"MARCUS-{product.asin}" if product else f"MARCUS-{listing.id}")

    attributes = {
        "item_name": [{"value": listing.title}],
        "bullet_point": [{"value": b} for b in (listing.bullets or [])],
        "product_description": [{"value": listing.description}],
        "generic_keyword": [{"value": listing.search_terms}],
    }
    if listing.brand_name:
        attributes["brand"] = [{"value": listing.brand_name}]

    logger.info(
        "Pushing SKU %s to %s (seller=%s, marketplace=%s)",
        sku, account.platform, spapi.seller_id, spapi.marketplace_id,
    )

    try:
        result = await spapi.create_listing(sku, {"attributes": attributes})
        if result:
            return {"success": True, "data": result, "sku": sku, "platform": account.platform}
        return {"success": False, "error": "SP-API listing creation returned no data"}
    except Exception as e:
        return {"success": False, "error": f"SP-API error: {e}"}


async def _push_fnac(
    listing: Listing, product: Product, account: MarketplaceAccount
) -> dict[str, Any]:
    logger.info("Fnac push: API integration pending - credentials needed")
    return {"success": False, "error": "Fnac API integration pending"}


async def _push_cdiscount(
    listing: Listing, product: Product, account: MarketplaceAccount
) -> dict[str, Any]:
    logger.info("CDiscount push: API integration pending")
    return {"success": False, "error": "CDiscount API integration pending"}
