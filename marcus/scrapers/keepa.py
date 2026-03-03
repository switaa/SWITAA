from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from marcus.config.settings import KEEPA_EMAIL, KEEPA_PASSWORD
from marcus.core.models import PriceHistory, Product
from marcus.utils.browser import BrowserManager

logger = logging.getLogger("marcus.keepa")

KEEPA_LOGIN_URL = "https://keepa.com/#!"
KEEPA_PRODUCT_URL = "https://keepa.com/#!product"

CONTEXT_NAME = "keepa"

KEEPA_DOMAIN_MAP = {
    "amazon_fr": "4",   # .fr
    "amazon_de": "3",   # .de
    "amazon_us": "1",   # .com
    "amazon_uk": "2",   # .co.uk
}


class KeepaScraper:
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self._page: Optional[Page] = None

    async def _get_page(self) -> Page:
        if self._page is None or self._page.is_closed():
            self._page = await self.browser.new_page(CONTEXT_NAME)
        return self._page

    async def is_logged_in(self) -> bool:
        page = await self._get_page()
        try:
            await page.goto(KEEPA_LOGIN_URL, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            logout_btn = page.locator('a:has-text("Log out"), a:has-text("Déconnexion"), #panelLogout')
            return await logout_btn.count() > 0
        except PlaywrightTimeout:
            return False

    async def login(self, email: str = "", password: str = "") -> bool:
        email = email or KEEPA_EMAIL
        password = password or KEEPA_PASSWORD

        if not email or not password:
            logger.error("Keepa credentials not configured in .env")
            return False

        page = await self._get_page()
        logger.info("Logging into Keepa...")

        try:
            await page.goto(KEEPA_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            login_link = page.locator('a:has-text("Log in"), a:has-text("Connexion"), #panelLogin')
            if await login_link.count() > 0:
                await login_link.click()
                await page.wait_for_timeout(1000)

            await page.fill('#username, input[name="username"]', email)
            await page.fill('#password, input[name="password"]', password)

            submit = page.locator('#submitLogin, button[type="submit"]').first
            await submit.click()
            await page.wait_for_timeout(5000)

            if await self.is_logged_in():
                logger.info("Keepa login successful")
                await self.browser.save_context(CONTEXT_NAME)
                return True

            logger.error("Keepa login failed")
            return False

        except PlaywrightTimeout:
            logger.error("Keepa login timed out")
            return False

    async def ensure_logged_in(self) -> bool:
        if await self.is_logged_in():
            logger.info("Already logged into Keepa (session restored)")
            return True
        return await self.login()

    async def get_product_data(self, asin: str, marketplace: str = "amazon_fr") -> Optional[dict]:
        """Fetch product data and price history from Keepa for a single ASIN."""
        if not await self.ensure_logged_in():
            logger.error("Cannot fetch Keepa data - not logged in")
            return None

        page = await self._get_page()
        domain_id = KEEPA_DOMAIN_MAP.get(marketplace, "4")

        try:
            url = f"{KEEPA_PRODUCT_URL}/{domain_id}-{asin}"
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(5000)

            data = await _extract_keepa_product(page, asin, marketplace)
            return data

        except PlaywrightTimeout:
            logger.error(f"Keepa product page timed out for {asin}")
            return None
        except Exception as e:
            logger.error(f"Keepa error for {asin}: {e}")
            return None

    async def enrich_products(self, products: list[Product]) -> list[Product]:
        """Enrich a list of products with Keepa data (price history, BSR trends)."""
        enriched = []
        for product in products:
            data = await self.get_product_data(product.asin, product.marketplace)
            if data:
                if data.get("current_price"):
                    product.price = data["current_price"]
                if data.get("bsr"):
                    product.bsr = data["bsr"]
                if data.get("rating"):
                    product.rating = data["rating"]
                if data.get("review_count"):
                    product.review_count = data["review_count"]
            enriched.append(product)
            await asyncio.sleep(2)
        return enriched

    async def get_price_history(self, asin: str, marketplace: str = "amazon_fr") -> list[PriceHistory]:
        """Extract price history entries from a Keepa product page."""
        data = await self.get_product_data(asin, marketplace)
        if not data or "price_history" not in data:
            return []
        return data["price_history"]

    async def close(self):
        if self._page and not self._page.is_closed():
            await self._page.close()


async def _extract_keepa_product(page: Page, asin: str, marketplace: str) -> dict:
    result: dict = {"asin": asin, "marketplace": marketplace, "price_history": []}

    stats_section = page.locator('#statisticContent, .product-stats, [data-testid="product-stats"]')
    if await stats_section.count() > 0:
        text = await stats_section.inner_text()
        result.update(_parse_stats_text(text))

    price_el = page.locator('.currentPrice, [data-testid="current-price"], #priceValue')
    if await price_el.count() > 0:
        price_text = await price_el.inner_text()
        import re
        nums = re.findall(r"[\d.,]+", price_text.replace(",", "."))
        if nums:
            result["current_price"] = float(nums[0])

    bsr_el = page.locator('.bsr-value, [data-testid="bsr"], #salesRank')
    if await bsr_el.count() > 0:
        bsr_text = await bsr_el.inner_text()
        import re
        nums = re.findall(r"[\d]+", bsr_text.replace(",", "").replace(".", ""))
        if nums:
            result["bsr"] = int(nums[0])

    return result


def _parse_stats_text(text: str) -> dict:
    import re
    result = {}

    rating_match = re.search(r"(\d[.,]\d)\s*/\s*5", text)
    if rating_match:
        result["rating"] = float(rating_match.group(1).replace(",", "."))

    review_match = re.search(r"([\d,. ]+)\s*(?:review|avis|rating)", text, re.IGNORECASE)
    if review_match:
        num = review_match.group(1).replace(",", "").replace(".", "").replace(" ", "")
        if num.isdigit():
            result["review_count"] = int(num)

    return result
