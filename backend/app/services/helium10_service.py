"""Helium 10 browser automation via Playwright (no API available)."""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright

from app.core.config import get_settings

logger = logging.getLogger("marcus.helium10")

BROWSER_STATE_DIR = Path("/app/data/browser_state")
H10_LOGIN_URL = "https://members.helium10.com/login"
H10_BLACKBOX_URL = "https://members.helium10.com/black-box"


class Helium10Service:
    def __init__(self):
        settings = get_settings()
        self.email = settings.HELIUM10_EMAIL
        self.password = settings.HELIUM10_PASSWORD
        self._pw = None
        self._browser = None

    async def _ensure_browser(self):
        if self._browser is None:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )

    async def _get_context(self):
        await self._ensure_browser()
        state_path = BROWSER_STATE_DIR / "helium10.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        storage = str(state_path) if state_path.exists() else None
        ctx = await self._browser.new_context(
            storage_state=storage,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        )
        return ctx

    async def _save_state(self, ctx):
        state_path = BROWSER_STATE_DIR / "helium10.json"
        await ctx.storage_state(path=str(state_path))

    async def login(self) -> bool:
        if not self.email or not self.password:
            logger.error("Helium 10 credentials not configured")
            return False

        ctx = await self._get_context()
        page = await ctx.new_page()
        try:
            await page.goto(H10_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            await page.fill('input[type="email"], input[name="email"]', self.email)
            await page.fill('input[type="password"], input[name="password"]', self.password)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)

            if "login" not in page.url.lower():
                logger.info("Helium 10 login successful")
                await self._save_state(ctx)
                return True

            logger.error("Helium 10 login failed")
            return False
        finally:
            await page.close()
            await ctx.close()

    async def search_black_box(
        self,
        marketplace: str = "amazon_fr",
        min_price: float = 10,
        max_price: float = 100,
        min_revenue: int = 1000,
        max_reviews: int = 200,
    ) -> list[dict[str, Any]]:
        ctx = await self._get_context()
        page = await ctx.new_page()
        products = []

        try:
            await page.goto(H10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower():
                logger.info("Session expired, re-logging in...")
                await page.close()
                await ctx.close()
                if not await self.login():
                    return []
                ctx = await self._get_context()
                page = await ctx.new_page()
                await page.goto(H10_BLACKBOX_URL, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

            search_btn = page.locator(
                'button:has-text("Search"), button:has-text("Rechercher"), '
                'button[data-testid="search-button"]'
            ).first
            if await search_btn.count() > 0:
                await search_btn.click()
                await page.wait_for_timeout(10000)

            products = await self._extract_products(page, marketplace)
            logger.info(f"Helium 10 Black Box: {len(products)} products found")
            await self._save_state(ctx)

        except Exception as e:
            logger.error(f"Helium 10 Black Box error: {e}")
        finally:
            await page.close()
            await ctx.close()

        return products

    async def _extract_products(self, page: Page, marketplace: str) -> list[dict[str, Any]]:
        products = []
        rows = page.locator("table tbody tr, .product-row, [data-testid='product-row']")
        count = await rows.count()

        for i in range(min(count, 100)):
            try:
                row = rows.nth(i)
                text = await row.inner_text()

                asin_match = re.search(r"B0[A-Z0-9]{8}", text)
                if not asin_match:
                    continue

                cells = row.locator("td")
                cell_count = await cells.count()
                if cell_count < 3:
                    continue

                title = (await cells.nth(1).inner_text()).strip()[:500]
                price = _extract_num(await cells.nth(2).inner_text() if cell_count > 2 else "")
                bsr = int(_extract_num(await cells.nth(4).inner_text())) if cell_count > 4 else None
                sales = int(_extract_num(await cells.nth(5).inner_text())) if cell_count > 5 else None
                reviews = int(_extract_num(await cells.nth(6).inner_text())) if cell_count > 6 else None

                products.append({
                    "asin": asin_match.group(0),
                    "title": title,
                    "price": price,
                    "marketplace": marketplace,
                    "bsr": bsr,
                    "monthly_sales": sales,
                    "review_count": reviews,
                    "source": "helium10",
                })
            except Exception:
                continue

        return products

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()


def _extract_num(text: str) -> float:
    nums = re.findall(r"[\d.,]+", text.replace(",", "."))
    return float(nums[0]) if nums else 0.0
