"""Test Amazon FR search to extract ASINs."""
import asyncio
import re
from playwright.async_api import async_playwright

ASIN_REGEX = re.compile(r"/dp/(B0[A-Z0-9]{8})")

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="fr-FR",
    )
    page = await ctx.new_page()

    keyword = "vanne 6 voies piscine"
    url = f"https://www.amazon.fr/s?k={keyword.replace(' ', '+')}"
    print(f"Searching: {url}")

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)
    print(f"Final URL: {page.url}")

    # Extract ASINs from product links
    html = await page.content()
    asins = list(dict.fromkeys(ASIN_REGEX.findall(html)))
    print(f"\nFound {len(asins)} unique ASINs:")
    for a in asins[:20]:
        print(f"  {a}")

    # Also extract titles and prices
    items = await page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('[data-asin]').forEach(el => {
            const asin = el.getAttribute('data-asin');
            if (!asin || !asin.startsWith('B0')) return;
            const titleEl = el.querySelector('h2 a span, .a-text-normal');
            const priceEl = el.querySelector('.a-price .a-offscreen');
            results.push({
                asin: asin,
                title: titleEl ? titleEl.textContent.trim().substring(0, 80) : '',
                price: priceEl ? priceEl.textContent.trim() : ''
            });
        });
        return results;
    }""")
    print(f"\nProduct details ({len(items)}):")
    for item in items[:15]:
        print(f"  {item['asin']} | {item['price']:>10} | {item['title']}")

    await page.screenshot(path="/app/data/debug/amazon_search_test.png")
    await browser.close()
    await pw.stop()

asyncio.run(main())
