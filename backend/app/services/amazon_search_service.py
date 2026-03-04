"""Amazon FR product search via Playwright - discovers ASINs by keyword."""
from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any

from playwright.async_api import async_playwright

logger = logging.getLogger("marcus.amazon_search")

ASIN_REGEX = re.compile(r"B0[A-Z0-9]{8}")
ASIN_DP_REGEX = re.compile(r"/dp/(B0[A-Z0-9]{8})")

MARKETPLACE_DOMAINS = {
    "amazon_fr": "www.amazon.fr",
    "amazon_de": "www.amazon.de",
    "amazon_uk": "www.amazon.co.uk",
    "amazon_us": "www.amazon.com",
}

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

MAX_PAGES = 3
MAX_RETRIES = 2


class AmazonSearchService:
    def __init__(self) -> None:
        self._pw = None
        self._browser = None

    async def _ensure_browser(self) -> None:
        if self._browser is None:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

    async def search_by_keyword(
        self,
        keyword: str,
        filters: dict[str, Any] | None = None,
        marketplace: str = "amazon_fr",
    ) -> list[dict[str, Any]]:
        """Search Amazon by keyword and extract product data from results."""
        filters = filters or {}
        domain = MARKETPLACE_DOMAINS.get(marketplace, "www.amazon.fr")
        all_products: list[dict[str, Any]] = []

        for attempt in range(MAX_RETRIES):
            try:
                await self._ensure_browser()
                ctx = await self._browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=STEALTH_USER_AGENT,
                    locale="fr-FR",
                    ignore_https_errors=True,
                )
                page = await ctx.new_page()

                for page_num in range(1, MAX_PAGES + 1):
                    url = f"https://{domain}/s?k={keyword.replace(' ', '+')}&page={page_num}"
                    logger.info(f"Searching: {url}")

                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(random.uniform(2, 4))

                    if "captcha" in page.url.lower() or "sorry" in (await page.title()).lower():
                        logger.warning("Amazon CAPTCHA detected, stopping pagination")
                        break

                    products = await self._extract_products(page, marketplace)
                    if not products:
                        break
                    all_products.extend(products)
                    logger.info(f"Page {page_num}: extracted {len(products)} products")

                    await asyncio.sleep(random.uniform(2, 5))

                await page.close()
                await ctx.close()

                seen = set()
                unique = []
                for p in all_products:
                    if p["asin"] not in seen:
                        seen.add(p["asin"])
                        unique.append(p)

                logger.info(f"Amazon search '{keyword}': {len(unique)} unique products found")
                return unique

            except Exception as e:
                logger.error(f"Amazon search error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(random.uniform(3, 6))

        return []

    async def _extract_products(self, page, marketplace: str) -> list[dict[str, Any]]:
        """Extract product data from Amazon search results page."""
        products: list[dict[str, Any]] = []

        items = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[data-asin]').forEach(el => {
                const asin = el.getAttribute('data-asin');
                if (!asin || asin.length !== 10 || !asin.startsWith('B0')) return;
                const titleEl = el.querySelector('h2 a span, h2 span.a-text-normal');
                const priceWhole = el.querySelector('.a-price .a-price-whole');
                const priceFrac = el.querySelector('.a-price .a-price-fraction');
                const ratingEl = el.querySelector('.a-icon-star-small .a-icon-alt, .a-icon-star .a-icon-alt');
                const reviewEl = el.querySelector('.a-size-base.s-underline-text, [data-csa-c-func-deps*="review"] .a-size-base');
                const imgEl = el.querySelector('img.s-image');

                let price = null;
                if (priceWhole) {
                    const w = priceWhole.textContent.replace(/[^0-9]/g, '');
                    const f = priceFrac ? priceFrac.textContent.replace(/[^0-9]/g, '') : '00';
                    price = parseFloat(w + '.' + f);
                }

                let rating = null;
                if (ratingEl) {
                    const m = ratingEl.textContent.match(/([0-9,]+)/);
                    if (m) rating = parseFloat(m[1].replace(',', '.'));
                }

                let reviewCount = null;
                if (reviewEl) {
                    const t = reviewEl.textContent.replace(/[^0-9]/g, '');
                    if (t) reviewCount = parseInt(t);
                }

                results.push({
                    asin: asin,
                    title: titleEl ? titleEl.textContent.trim().substring(0, 500) : '',
                    price: price,
                    rating: rating,
                    review_count: reviewCount,
                    image_url: imgEl ? imgEl.src : '',
                });
            });
            return results;
        }""")

        for item in items:
            products.append({
                "asin": item["asin"],
                "title": item.get("title", ""),
                "price": item.get("price"),
                "rating": item.get("rating"),
                "review_count": item.get("review_count"),
                "image_url": item.get("image_url", ""),
                "marketplace": marketplace,
                "source": "amazon_search",
            })

        return products

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
