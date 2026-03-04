"""Keepa API client for product data and price history."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("marcus.keepa")

KEEPA_API_BASE = "https://api.keepa.com"
DOMAIN_MAP = {"amazon_fr": 4, "amazon_de": 3, "amazon_us": 1, "amazon_uk": 2}


class KeepaClient:
    def __init__(self):
        self.api_key = get_settings().KEEPA_API_KEY

    async def get_product(self, asin: str, marketplace: str = "amazon_fr") -> dict[str, Any] | None:
        if not self.api_key:
            logger.error("Keepa API key not configured")
            return None

        domain = DOMAIN_MAP.get(marketplace, 4)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{KEEPA_API_BASE}/product",
                params={"key": self.api_key, "domain": domain, "asin": asin, "stats": 180},
            )
            if resp.status_code != 200:
                logger.error(f"Keepa API error {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            products = data.get("products", [])
            if not products:
                return None

            return _parse_keepa_product(products[0], marketplace)

    async def search_by_category(
        self, category_id: int, marketplace: str = "amazon_fr", limit: int = 50
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            return []

        domain = DOMAIN_MAP.get(marketplace, 4)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{KEEPA_API_BASE}/bestsellers",
                params={"key": self.api_key, "domain": domain, "category": category_id},
            )
            if resp.status_code != 200:
                logger.error(f"Keepa bestsellers error: {resp.status_code}")
                return []

            data = resp.json()
            asins = data.get("asinList", [])[:limit]

            results = []
            for asin in asins:
                product = await self.get_product(asin, marketplace)
                if product:
                    results.append(product)

            return results

    async def tokens_left(self) -> int:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{KEEPA_API_BASE}/token", params={"key": self.api_key}
            )
            if resp.status_code == 200:
                return resp.json().get("tokensLeft", 0)
        return 0


def _parse_keepa_product(raw: dict, marketplace: str) -> dict[str, Any]:
    stats = raw.get("stats", {})
    csv_data = raw.get("csv", [])

    current_price = None
    if stats.get("current"):
        prices = stats["current"]
        if len(prices) > 0 and prices[0] is not None and prices[0] > 0:
            current_price = prices[0] / 100
        elif len(prices) > 1 and prices[1] is not None and prices[1] > 0:
            current_price = prices[1] / 100

    avg_price = None
    if stats.get("avg") and len(stats["avg"]) > 0:
        vals = [v / 100 for v in stats["avg"] if v is not None and v > 0]
        avg_price = sum(vals) / len(vals) if vals else None

    bsr = None
    if stats.get("current") and len(stats["current"]) > 3:
        bsr_val = stats["current"][3]
        if bsr_val is not None and bsr_val > 0:
            bsr = bsr_val

    sales_rank_drops = stats.get("salesRankDrops30", 0)
    monthly_sales = sales_rank_drops * 1 if sales_rank_drops else None

    return {
        "asin": raw.get("asin", ""),
        "title": raw.get("title", ""),
        "brand": raw.get("brand", ""),
        "category": raw.get("categoryTree", [{}])[-1].get("name", "") if raw.get("categoryTree") else "",
        "price": current_price or avg_price or 0,
        "marketplace": marketplace,
        "bsr": bsr,
        "monthly_sales": monthly_sales,
        "review_count": raw.get("totalRatings", 0),
        "rating": raw.get("rating", 0),
        "seller_count": raw.get("numberOfOffers", 0),
        "image_url": f"https://images-na.ssl-images-amazon.com/images/I/{raw.get('imagesCSV', '').split(',')[0]}" if raw.get("imagesCSV") else "",
        "source": "keepa",
        "raw_data": raw,
    }
