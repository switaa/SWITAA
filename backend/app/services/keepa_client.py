"""Keepa API client for product data and price history."""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("marcus.keepa")

KEEPA_API_BASE = "https://api.keepa.com"
DOMAIN_MAP = {"amazon_fr": 4, "amazon_de": 3, "amazon_us": 1, "amazon_uk": 2}

# Keepa CSV indices: 0=Amazon, 1=New, 2=Used, 3=SalesRank, ...
CSV_AMAZON = 0
CSV_NEW = 1
CSV_USED = 2
CSV_SALES_RANK = 3

# Amazon seller ID in buyBoxSellerIdHistory (0 = Amazon)
AMAZON_SELLER_ID = 0


def _extract_prices_from_csv(csv_array: list[list[int]] | None, price_index: int = CSV_NEW) -> list[float]:
    """Extract valid prices from Keepa CSV history for last 90 days.
    CSV format: [time0, val0, time1, val1, ...], values in cents, -1 = no data.
    """
    if not csv_array or price_index >= len(csv_array):
        return []
    history = csv_array[price_index]
    if not history or len(history) < 2:
        return []
    # Get last timestamp as reference for 90 days
    last_ts = history[-2] if len(history) % 2 == 0 else history[-1]
    cutoff_ts = last_ts - (90 * 24 * 60)  # 90 days in minutes
    prices: list[float] = []
    i = 0
    while i < len(history) - 1:
        ts, val = history[i], history[i + 1]
        if ts >= cutoff_ts and val is not None and val > 0:
            prices.append(val / 100.0)
        i += 2
    return prices


def _compute_price_stability(prices: list[float]) -> str:
    """Compute price stability from price list over 90 days."""
    if len(prices) < 2:
        return "unknown"
    avg = sum(prices) / len(prices)
    if avg <= 0:
        return "unknown"
    variance = sum((p - avg) ** 2 for p in prices) / len(prices)
    stddev = math.sqrt(variance)
    cv = (stddev / avg) * 100  # coefficient of variation in %

    # Check trending down: compare last 25% vs first 25%
    n = len(prices)
    if n >= 8:
        recent_avg = sum(prices[-n // 4 :]) / (n // 4)
        older_avg = sum(prices[: n // 4]) / (n // 4)
        if recent_avg < older_avg * 0.95:  # >5% drop
            return "trending_down"

    if cv < 5:
        return "stable"
    if cv <= 15:
        return "moderate"
    return "volatile"


def _get_buybox_info(raw: dict) -> tuple[bool, str | None, float | None]:
    """Extract BuyBox info: amazon_is_seller, buybox_seller, buybox_price."""
    amazon_is_seller = False
    buybox_seller: str | None = None
    buybox_price: float | None = None

    # buyBoxSellerIdHistory: 0 = Amazon, 1 = 3rd party
    seller_history = raw.get("buyBoxSellerIdHistory")
    if seller_history:
        # CSV format [t0, v0, t1, v1, ...], get last value
        if len(seller_history) >= 2:
            last_seller_id = seller_history[-1]
            amazon_is_seller = last_seller_id == AMAZON_SELLER_ID
            buybox_seller = "Amazon" if amazon_is_seller else "3rd_party"

    # buyBoxPriceHistory or use stats current for buybox price
    buybox_history = raw.get("buyBoxNewHistory") or raw.get("buyBoxAmazonHistory")
    if buybox_history and len(buybox_history) >= 2:
        buybox_price = buybox_history[-1] / 100.0 if buybox_history[-1] > 0 else None
    if buybox_price is None:
        stats = raw.get("stats", {})
        current = stats.get("current", [])
        if len(current) > CSV_NEW and current[CSV_NEW] and current[CSV_NEW] > 0:
            buybox_price = current[CSV_NEW] / 100.0
        elif len(current) > CSV_AMAZON and current[CSV_AMAZON] and current[CSV_AMAZON] > 0:
            buybox_price = current[CSV_AMAZON] / 100.0

    return amazon_is_seller, buybox_seller, buybox_price


def _parse_enriched_product(
    raw: dict, marketplace: str, category_multiplier: float = 1.5
) -> dict[str, Any]:
    """Parse Keepa product with enriched data."""
    stats = raw.get("stats", {})
    csv_data = raw.get("csv", [])

    # Price: prefer current New, then Amazon, then avg
    current_price: float | None = None
    if stats.get("current"):
        prices = stats["current"]
        for idx in (CSV_NEW, CSV_AMAZON):
            if len(prices) > idx and prices[idx] is not None and prices[idx] > 0:
                current_price = prices[idx] / 100
                break
    if current_price is None and stats.get("avg"):
        vals = [v / 100 for v in stats["avg"] if v is not None and v > 0]
        current_price = sum(vals) / len(vals) if vals else None
    price = current_price or 0.0

    # BSR
    bsr: int | None = None
    if stats.get("current") and len(stats["current"]) > CSV_SALES_RANK:
        bsr_val = stats["current"][CSV_SALES_RANK]
        if bsr_val is not None and bsr_val > 0:
            bsr = bsr_val

    # Monthly sales: salesRankDrops30 * category multiplier (default 1.5)
    sales_rank_drops = stats.get("salesRankDrops30", 0) or 0
    monthly_sales = int(sales_rank_drops * category_multiplier) if sales_rank_drops else None

    # BuyBox info
    amazon_is_seller, buybox_seller, buybox_price = _get_buybox_info(raw)

    # Price stability from csv data (90 days)
    prices_90d = _extract_prices_from_csv(csv_data, CSV_NEW)
    if not prices_90d:
        prices_90d = _extract_prices_from_csv(csv_data, CSV_AMAZON)
    price_stability = _compute_price_stability(prices_90d)

    # Image URL
    images_csv = raw.get("imagesCSV", "")
    image_url = ""
    if images_csv:
        first_img = images_csv.split(",")[0]
        if first_img:
            image_url = f"https://images-na.ssl-images-amazon.com/images/I/{first_img}"

    # Category
    category_tree = raw.get("categoryTree", [])
    category = category_tree[-1].get("name", "") if category_tree else ""

    return {
        "asin": raw.get("asin", ""),
        "title": raw.get("title", ""),
        "brand": raw.get("brand", ""),
        "category": category,
        "price": price,
        "bsr": bsr,
        "monthly_sales": monthly_sales,
        "review_count": raw.get("totalRatings", 0),
        "rating": raw.get("rating", 0),
        "seller_count": raw.get("numberOfOffers", 0),
        "image_url": image_url,
        "amazon_is_seller": amazon_is_seller,
        "buybox_seller": buybox_seller,
        "buybox_price": buybox_price,
        "price_stability": price_stability,
        "source": "keepa",
        "raw_data": raw,
    }


def _parse_keepa_product(raw: dict, marketplace: str) -> dict[str, Any]:
    """Legacy parser for get_product - returns enriched structure."""
    return _parse_enriched_product(raw, marketplace, category_multiplier=1.5)


class KeepaClient:
    def __init__(self) -> None:
        self.api_key = get_settings().KEEPA_API_KEY

    async def get_product(self, asin: str, marketplace: str = "amazon_fr") -> dict[str, Any] | None:
        """Fetch a single product by ASIN."""
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

    async def tokens_left(self) -> int:
        """Return remaining Keepa API tokens."""
        if not self.api_key:
            return 0
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{KEEPA_API_BASE}/token",
                params={"key": self.api_key},
            )
            if resp.status_code == 200:
                return resp.json().get("tokensLeft", 0)
        return 0

    async def enrich_batch(
        self,
        asins: list[str],
        marketplace: str = "amazon_fr",
        category_multiplier: float = 1.5,
    ) -> list[dict[str, Any]]:
        """Enrich up to 100 ASINs per request with full product data.
        Checks tokens before each batch, waits 60s if below 10.
        """
        if not self.api_key:
            logger.error("Keepa API key not configured")
            return []

        domain = DOMAIN_MAP.get(marketplace, 4)
        results: list[dict[str, Any]] = []
        asin_list = list(dict.fromkeys(asins))  # dedupe preserving order

        batch_size = 100
        for i in range(0, len(asin_list), batch_size):
            batch = asin_list[i : i + batch_size]

            # Check tokens before each batch
            tokens = await self.tokens_left()
            if tokens < 10:
                logger.warning(f"Keepa tokens low ({tokens}), waiting 60s")
                await asyncio.sleep(60)
                tokens = await self.tokens_left()
                if tokens < 10:
                    logger.error("Keepa tokens still low after wait, skipping batch")
                    continue

            asin_param = ",".join(batch)
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(
                    f"{KEEPA_API_BASE}/product",
                    params={
                        "key": self.api_key,
                        "domain": domain,
                        "asin": asin_param,
                        "stats": 180,
                    },
                )
                if resp.status_code != 200:
                    logger.error(f"Keepa batch error {resp.status_code}: {resp.text[:200]}")
                    continue

                data = resp.json()
                products = data.get("products", [])

                for raw in products:
                    try:
                        enriched = _parse_enriched_product(
                            raw, marketplace, category_multiplier=category_multiplier
                        )
                        results.append(enriched)
                    except Exception as e:
                        logger.exception("Error parsing Keepa product %s: %s", raw.get("asin"), e)

        return results
