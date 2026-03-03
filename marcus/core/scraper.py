from __future__ import annotations

import asyncio
import logging

from marcus.config.settings import DB_PATH
from marcus.core.analyzer import ProductAnalyzer
from marcus.core.models import Database
from marcus.scrapers.helium10 import Helium10Scraper
from marcus.scrapers.keepa import KeepaScraper
from marcus.utils.browser import BrowserManager

logger = logging.getLogger("marcus.scraper")


class MarcusScraper:
    """Orchestrates the full scraping pipeline: Helium 10 -> Keepa -> Analysis -> DB."""

    def __init__(self, headless: bool = True):
        self.browser = BrowserManager(headless=headless)
        self.db = Database(DB_PATH)
        self.helium10 = Helium10Scraper(self.browser)
        self.keepa = KeepaScraper(self.browser)
        self.analyzer = ProductAnalyzer(self.db)

    async def start(self):
        await self.browser.start()
        logger.info("Marcus scraper started")

    async def run_search(
        self,
        marketplace: str = "amazon_fr",
        min_price: float = 10,
        max_price: float = 100,
        min_revenue: int = 1000,
        max_reviews: int = 200,
        min_sales: int = 100,
        category: str = "",
        enrich_with_keepa: bool = True,
        min_score: float = 40,
        cost_price: float | None = None,
    ) -> list:
        """Full pipeline: search -> enrich -> analyze -> save."""
        logger.info(f"Starting search on {marketplace}")

        products = await self.helium10.search_black_box(
            marketplace=marketplace,
            min_price=min_price,
            max_price=max_price,
            min_revenue=min_revenue,
            max_reviews=max_reviews,
            min_sales=min_sales,
            category=category,
        )

        if not products:
            logger.warning("No products found from Helium 10")
            return []

        logger.info(f"Found {len(products)} products from Helium 10")

        if enrich_with_keepa:
            logger.info("Enriching with Keepa data...")
            products = await self.keepa.enrich_products(products)

        for p in products:
            self.db.upsert_product(p)

        opportunities = self.analyzer.analyze_batch(products, cost_price, min_score)
        self.analyzer.save_opportunities(opportunities)

        logger.info(f"Pipeline complete: {len(opportunities)} opportunities found")
        return opportunities

    async def close(self):
        await self.helium10.close()
        await self.keepa.close()
        await self.browser.close()
        self.db.close()
        logger.info("Marcus scraper shut down")
