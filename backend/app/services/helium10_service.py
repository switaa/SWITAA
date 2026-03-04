"""Helium 10 browser automation via Playwright (no API available)."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright

from app.core.config import get_settings

logger = logging.getLogger("marcus.helium10")

BROWSER_STATE_DIR = Path("/app/data/browser_state")
DEBUG_DIR = Path("/app/data/debug")
H10_LOGIN_URL = "https://members.helium10.com/login"
H10_BLACKBOX_URL = "https://members.helium10.com/black-box"

ASIN_REGEX = re.compile(r"B0[A-Z0-9]{8}")

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

MAX_RETRIES = 3
MAX_PAGES = 3


def _random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> float:
    """Return random delay in seconds for anti-detection."""
    return random.uniform(min_sec, max_sec)


def _extract_num(text: str) -> float:
    nums = re.findall(r"[\d.,]+", str(text).replace(",", "."))
    return float(nums[0]) if nums else 0.0


class Helium10Service:
    def __init__(self) -> None:
        settings = get_settings()
        self.email = settings.HELIUM10_EMAIL
        self.password = settings.HELIUM10_PASSWORD
        self._pw = None
        self._browser = None

    async def _ensure_browser(self) -> None:
        if self._browser is None:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

    async def _get_context(self):
        await self._ensure_browser()
        state_path = BROWSER_STATE_DIR / "helium10.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        storage = str(state_path) if state_path.exists() else None
        ctx = await self._browser.new_context(
            storage_state=storage,
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
            ignore_https_errors=True,
        )
        return ctx

    async def _save_state(self, ctx) -> None:
        state_path = BROWSER_STATE_DIR / "helium10.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        await ctx.storage_state(path=str(state_path))

    async def _screenshot_on_error(self, page: Page, prefix: str = "helium10") -> None:
        """Save screenshot to debug directory on error."""
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            path = DEBUG_DIR / f"{prefix}_error_{ts}.png"
            await page.screenshot(path=str(path))
            logger.warning(f"Screenshot saved to {path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

    async def _random_wait(self, min_sec: float = 2.0, max_sec: float = 5.0) -> None:
        delay = _random_delay(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def login(self) -> bool:
        if not self.email or not self.password:
            logger.error("Helium 10 credentials not configured")
            return False

        ctx = await self._get_context()
        page = await ctx.new_page()
        try:
            await page.goto(H10_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await self._random_wait(2, 4)

            await page.fill('input[type="email"], input[name="email"]', self.email)
            await self._random_wait(1, 2)
            await page.fill('input[type="password"], input[name="password"]', self.password)
            await self._random_wait(1, 2)
            await page.click('button[type="submit"]')
            await self._random_wait(4, 6)

            if "login" not in page.url.lower():
                logger.info("Helium 10 login successful")
                await self._save_state(ctx)
                return True

            logger.error("Helium 10 login failed")
            await self._screenshot_on_error(page, "helium10_login")
            return False
        except Exception as e:
            logger.error(f"Helium 10 login error: {e}")
            await self._screenshot_on_error(page, "helium10_login")
            return False
        finally:
            await page.close()
            await ctx.close()

    async def search_by_keyword(
        self,
        keyword: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search Black Box by keyword with optional filters.
        Filters: min_price, max_price, max_reviews, marketplace.
        Supports pagination up to 3 pages.
        """
        filters = filters or {}
        min_price = filters.get("min_price")
        max_price = filters.get("max_price")
        max_reviews = filters.get("max_reviews")
        marketplace = filters.get("marketplace", "amazon_fr")

        all_products: list[dict[str, Any]] = []

        for attempt in range(MAX_RETRIES):
            ctx = None
            page = None
            try:
                ctx = await self._get_context()
                page = await ctx.new_page()

                await page.goto(H10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=30000)
                await self._random_wait(3, 5)

                if "login" in page.url.lower():
                    logger.info("Session expired, re-logging in...")
                    await page.close()
                    await ctx.close()
                    if not await self.login():
                        return []
                    ctx = await self._get_context()
                    page = await ctx.new_page()
                    await page.goto(H10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=30000)
                    await self._random_wait(3, 5)

                keyword_input = page.locator(
                    'input[placeholder*="keyword"], input[placeholder*="Keyword"], '
                    'input[name="keyword"], input[type="text"][data-testid*="keyword"], '
                    '#keyword, .keyword-input'
                ).first
                if await keyword_input.count() > 0:
                    await keyword_input.fill(keyword)
                    await self._random_wait(1, 2)

                if min_price is not None:
                    min_price_el = page.locator(
                        'input[name*="min_price"], input[placeholder*="Min"], '
                        'input[data-testid*="min-price"]'
                    ).first
                    if await min_price_el.count() > 0:
                        await min_price_el.fill(str(min_price))
                        await self._random_wait(0.5, 1)

                if max_price is not None:
                    max_price_el = page.locator(
                        'input[name*="max_price"], input[placeholder*="Max"], '
                        'input[data-testid*="max-price"]'
                    ).first
                    if await max_price_el.count() > 0:
                        await max_price_el.fill(str(max_price))
                        await self._random_wait(0.5, 1)

                if max_reviews is not None:
                    max_reviews_el = page.locator(
                        'input[name*="reviews"], input[placeholder*="review"], '
                        'input[data-testid*="reviews"]'
                    ).first
                    if await max_reviews_el.count() > 0:
                        await max_reviews_el.fill(str(max_reviews))
                        await self._random_wait(0.5, 1)

                if marketplace:
                    marketplace_select = page.locator(
                        'select[name*="marketplace"], select[data-testid*="marketplace"], '
                        '.marketplace-select'
                    ).first
                    if await marketplace_select.count() > 0:
                        await marketplace_select.select_option(label=marketplace)
                        await self._random_wait(0.5, 1)

                search_btn = page.locator(
                    'button:has-text("Search"), button:has-text("Rechercher"), '
                    'button[data-testid="search-button"], button[type="submit"]'
                ).first
                if await search_btn.count() > 0:
                    await search_btn.click()
                    await self._random_wait(5, 8)

                for page_num in range(MAX_PAGES):
                    products = await self._extract_products(page, marketplace)
                    all_products.extend(products)
                    logger.info(f"Page {page_num + 1}: extracted {len(products)} products")

                    if page_num < MAX_PAGES - 1:
                        next_btn = page.locator(
                            'button:has-text("Next"), a:has-text("Next"), '
                            '[data-testid="next-page"], .pagination-next, [aria-label="Next"]'
                        ).first
                        if await next_btn.count() > 0 and await next_btn.is_enabled():
                            await next_btn.click()
                            await self._random_wait(3, 5)
                        else:
                            break

                seen_asins = set()
                unique_products = []
                for p in all_products:
                    if p["asin"] not in seen_asins:
                        seen_asins.add(p["asin"])
                        unique_products.append(p)

                logger.info(f"Helium 10 Black Box: {len(unique_products)} unique products found")
                await self._save_state(ctx)
                return unique_products

            except Exception as e:
                logger.error(f"Helium 10 Black Box error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if page:
                    await self._screenshot_on_error(page, f"helium10_search_attempt{attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    await self._random_wait(3, 6)
            finally:
                if page:
                    await page.close()
                if ctx:
                    await ctx.close()

        return []

    async def _extract_products(self, page: Page, marketplace: str) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        rows = page.locator(
            "table tbody tr, .product-row, [data-testid='product-row'], "
            ".black-box-row, tr[data-product]"
        )
        count = await rows.count()

        for i in range(min(count, 100)):
            try:
                row = rows.nth(i)
                text = await row.inner_text()

                asin_match = ASIN_REGEX.search(text)
                if not asin_match:
                    continue

                asin = asin_match.group(0)

                cells = row.locator("td")
                cell_count = await cells.count()

                title = ""
                price: float | None = None
                bsr: int | None = None
                monthly_sales: int | None = None
                review_count: int | None = None
                seller_count: int | None = None

                if cell_count >= 2:
                    title = (await cells.nth(1).inner_text()).strip()[:500]
                if cell_count >= 3:
                    price = _extract_num(await cells.nth(2).inner_text())
                if cell_count >= 5:
                    bsr = int(_extract_num(await cells.nth(4).inner_text()))
                if cell_count >= 6:
                    monthly_sales = int(_extract_num(await cells.nth(5).inner_text()))
                if cell_count >= 7:
                    review_count = int(_extract_num(await cells.nth(6).inner_text()))
                if cell_count >= 8:
                    seller_count = int(_extract_num(await cells.nth(7).inner_text()))

                products.append({
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "marketplace": marketplace,
                    "bsr": bsr,
                    "monthly_sales": monthly_sales,
                    "review_count": review_count,
                    "seller_count": seller_count,
                    "source": "helium10",
                })
            except Exception as ex:
                logger.debug(f"Skip row {i}: {ex}")
                continue

        return products

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
