from __future__ import annotations

import asyncio
import logging
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from marcus.config.settings import HELIUM10_EMAIL, HELIUM10_PASSWORD
from marcus.core.models import Product
from marcus.utils.browser import BrowserManager

logger = logging.getLogger("marcus.helium10")

HELIUM10_LOGIN_URL = "https://members.helium10.com/login"
HELIUM10_BLACKBOX_URL = "https://members.helium10.com/black-box"

CONTEXT_NAME = "helium10"


class Helium10Scraper:
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
            await page.goto(HELIUM10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            if "login" in page.url.lower():
                return False
            return True
        except PlaywrightTimeout:
            return False

    async def login(self, email: str = "", password: str = "") -> bool:
        email = email or HELIUM10_EMAIL
        password = password or HELIUM10_PASSWORD

        if not email or not password:
            logger.error("Helium 10 credentials not configured in .env")
            return False

        page = await self._get_page()
        logger.info("Logging into Helium 10...")

        try:
            await page.goto(HELIUM10_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            await page.fill('input[name="email"], input[type="email"]', email)
            await page.fill('input[name="password"], input[type="password"]', password)

            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)

            if "login" not in page.url.lower():
                logger.info("Helium 10 login successful")
                await self.browser.save_context(CONTEXT_NAME)
                return True

            logger.error("Helium 10 login failed - still on login page")
            return False

        except PlaywrightTimeout:
            logger.error("Helium 10 login timed out")
            return False

    async def ensure_logged_in(self) -> bool:
        if await self.is_logged_in():
            logger.info("Already logged into Helium 10 (session restored)")
            return True
        return await self.login()

    async def search_black_box(
        self,
        marketplace: str = "amazon_fr",
        min_price: float = 10,
        max_price: float = 100,
        min_revenue: int = 1000,
        max_reviews: int = 200,
        min_sales: int = 100,
        category: str = "",
    ) -> list[Product]:
        """Search products using Helium 10 Black Box with given filters."""
        if not await self.ensure_logged_in():
            logger.error("Cannot search - not logged in")
            return []

        page = await self._get_page()
        products = []

        try:
            await page.goto(HELIUM10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            marketplace_domain = _marketplace_to_h10(marketplace)
            marketplace_selector = page.locator('[data-testid="marketplace-select"], .marketplace-selector')
            if await marketplace_selector.count() > 0:
                await marketplace_selector.click()
                await page.wait_for_timeout(500)
                option = page.locator(f'text="{marketplace_domain}"').first
                if await option.count() > 0:
                    await option.click()
                    await page.wait_for_timeout(500)

            filter_map = {
                "min_price": min_price,
                "max_price": max_price,
                "min_revenue": min_revenue,
                "max_reviews": max_reviews,
                "min_sales": min_sales,
            }
            await _fill_filters(page, filter_map)

            if category:
                cat_selector = page.locator('[data-testid="category-select"], .category-dropdown')
                if await cat_selector.count() > 0:
                    await cat_selector.click()
                    await page.wait_for_timeout(500)
                    cat_option = page.locator(f'text="{category}"').first
                    if await cat_option.count() > 0:
                        await cat_option.click()

            search_btn = page.locator('button:has-text("Search"), button:has-text("Rechercher"), button[data-testid="search-button"]').first
            if await search_btn.count() > 0:
                await search_btn.click()
                logger.info("Black Box search launched, waiting for results...")
                await page.wait_for_timeout(10000)

            products = await _extract_products(page, marketplace, "helium10_blackbox")
            logger.info(f"Found {len(products)} products from Black Box")

        except PlaywrightTimeout:
            logger.error("Black Box search timed out")
        except Exception as e:
            logger.error(f"Black Box search error: {e}")

        return products

    async def close(self):
        if self._page and not self._page.is_closed():
            await self._page.close()


def _marketplace_to_h10(marketplace: str) -> str:
    mapping = {
        "amazon_fr": "amazon.fr",
        "amazon_de": "amazon.de",
        "amazon_us": "amazon.com",
        "amazon_uk": "amazon.co.uk",
    }
    return mapping.get(marketplace, "amazon.fr")


async def _fill_filters(page: Page, filters: dict):
    for field, value in filters.items():
        if value is None:
            continue
        selector = f'input[data-testid="{field}"], input[name="{field}"], input[placeholder*="{field}"]'
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.fill(str(value))
            await page.wait_for_timeout(300)


async def _extract_products(page: Page, marketplace: str, source: str) -> list[Product]:
    products = []
    rows = page.locator("table tbody tr, .product-row, [data-testid='product-row']")
    count = await rows.count()

    for i in range(min(count, 100)):
        try:
            row = rows.nth(i)
            cells = row.locator("td")
            cell_count = await cells.count()

            if cell_count < 3:
                continue

            title = await _safe_text(cells.nth(1))
            asin = await _extract_asin(row)
            price = await _extract_number(cells, [2, 3])
            bsr = await _extract_int(cells, [4, 5])
            sales = await _extract_int(cells, [5, 6])
            reviews = await _extract_int(cells, [6, 7])
            rating = await _extract_number(cells, [7, 8])

            if not asin or not title:
                continue

            products.append(Product(
                asin=asin,
                title=title,
                price=price,
                marketplace=marketplace,
                bsr=bsr if bsr else None,
                monthly_sales=sales if sales else None,
                review_count=reviews if reviews else None,
                rating=rating if rating else None,
                source=source,
            ))
        except Exception:
            continue

    return products


async def _safe_text(locator) -> str:
    try:
        return (await locator.inner_text()).strip()
    except Exception:
        return ""


async def _extract_asin(row) -> str:
    try:
        asin_el = row.locator('[data-asin], [data-testid="asin"]')
        if await asin_el.count() > 0:
            return await asin_el.get_attribute("data-asin") or await asin_el.inner_text()
        text = await row.inner_text()
        import re
        match = re.search(r"B0[A-Z0-9]{8}", text)
        return match.group(0) if match else ""
    except Exception:
        return ""


async def _extract_number(cells, indices: list[int]) -> float:
    for idx in indices:
        if idx >= await cells.count():
            continue
        try:
            text = await cells.nth(idx).inner_text()
            import re
            nums = re.findall(r"[\d.,]+", text.replace(",", "."))
            if nums:
                return float(nums[0])
        except Exception:
            continue
    return 0.0


async def _extract_int(cells, indices: list[int]) -> int:
    val = await _extract_number(cells, indices)
    return int(val) if val else 0
