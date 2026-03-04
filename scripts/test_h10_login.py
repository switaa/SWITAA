"""Test Helium 10 login page structure."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    page = await ctx.new_page()

    await page.goto("https://members.helium10.com/user/signin", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    print(f"URL: {page.url}")
    print(f"Title: {await page.title()}")

    inputs = await page.evaluate("""() => {
        const els = document.querySelectorAll('input');
        return Array.from(els).map(el => ({
            type: el.type, name: el.name, id: el.id, placeholder: el.placeholder,
            class: el.className.substring(0, 80), ariaLabel: el.getAttribute('aria-label')
        }));
    }""")
    print("\nInputs found:")
    for inp in inputs:
        print(f"  {inp}")

    buttons = await page.evaluate("""() => {
        const els = document.querySelectorAll('button, input[type=submit]');
        return Array.from(els).map(el => ({
            type: el.type, text: el.textContent.trim().substring(0, 50),
            id: el.id, class: el.className.substring(0, 80)
        }));
    }""")
    print("\nButtons found:")
    for btn in buttons:
        print(f"  {btn}")

    # Take screenshot
    await page.screenshot(path="/app/data/debug/h10_signin_page.png")
    print("\nScreenshot saved")

    await browser.close()
    await pw.stop()

asyncio.run(main())
