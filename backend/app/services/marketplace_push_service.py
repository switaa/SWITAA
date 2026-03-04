"""Push listings to marketplaces (Amazon, Fnac, Rue du Commerce)."""
from __future__ import annotations

import logging
from typing import Any

from app.core.database import SessionLocal
from app.models.listing import Listing
from app.models.marketplace import MarketplaceAccount, PushLog
from app.models.product import Product

logger = logging.getLogger("marcus.marketplace_push")


async def push_to_marketplace(push_log_id: str):
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

        product = db.query(Product).filter(Product.id == listing.product_id).first()

        logger.info(f"Pushing listing {listing.id} to {account.platform}")

        if account.platform.startswith("amazon"):
            result = await _push_amazon(listing, product, account)
        elif account.platform == "fnac":
            result = await _push_fnac(listing, product, account)
        elif account.platform == "rdc":
            result = await _push_rdc(listing, product, account)
        else:
            result = {"success": False, "error": f"Unsupported platform: {account.platform}"}

        if result.get("success"):
            log.status = "success"
            log.response_data = result
            listing.status = "published"
        else:
            log.status = "error"
            log.error_message = result.get("error", "Unknown error")
            log.response_data = result

        db.commit()
        logger.info(f"Push result for {listing.id}: {log.status}")

    except Exception as e:
        logger.error(f"Push error: {e}")
        if log:
            log.status = "error"
            log.error_message = str(e)
            db.commit()
    finally:
        db.close()


async def _push_amazon(listing: Listing, product: Product, account: MarketplaceAccount) -> dict[str, Any]:
    from app.services.spapi_client import SPAPIClient

    spapi = SPAPIClient()
    sku = f"MARCUS-{product.asin}" if product else f"MARCUS-{listing.id}"

    attributes = {
        "item_name": [{"value": listing.title}],
        "bullet_point": [{"value": b} for b in (listing.bullets or [])],
        "product_description": [{"value": listing.description}],
        "generic_keyword": [{"value": listing.search_terms}],
    }
    if listing.brand_name:
        attributes["brand"] = [{"value": listing.brand_name}]

    result = await spapi.create_listing(sku, {"attributes": attributes})
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "SP-API listing creation failed"}


async def _push_fnac(listing: Listing, product: Product, account: MarketplaceAccount) -> dict[str, Any]:
    # Fnac Marketplace API integration placeholder
    logger.info("Fnac push: API integration pending - credentials needed")
    return {"success": False, "error": "Fnac API integration pending"}


async def _push_rdc(listing: Listing, product: Product, account: MarketplaceAccount) -> dict[str, Any]:
    # Rue du Commerce API integration placeholder
    logger.info("Rue du Commerce push: API integration pending")
    return {"success": False, "error": "Rue du Commerce API integration pending"}
