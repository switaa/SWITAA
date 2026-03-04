"""Full login + Black Box test."""
import asyncio
from playwright.async_api import async_playwright
from app.core.config import get_settings

async def main():
    settings = get_settings()
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    page = await ctx.new_page()

    # Login
    print("--- Step 1: Login ---")
    await page.goto("https://members.helium10.com/user/signin", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)
    
    await page.fill("#loginform-email", settings.HELIUM10_EMAIL)
    await asyncio.sleep(1)
    await page.fill("#loginform-password", settings.HELIUM10_PASSWORD)
    await asyncio.sleep(1)
    await page.click('button[type="submit"]')
    await asyncio.sleep(8)

    print(f"After login URL: {page.url}")
    await page.screenshot(path="/app/data/debug/h10_after_login.png")

    if "signin" in page.url.lower():
        print("LOGIN FAILED - still on signin page")
        # Check for error messages
        errors = await page.evaluate("""() => {
            const els = document.querySelectorAll('.help-block, .error-summary, .alert, .error');
            return Array.from(els).map(el => el.textContent.trim());
        }""")
        print("Errors:", errors)
        await browser.close()
        await pw.stop()
        return

    print("LOGIN SUCCESS")

    # Go to Black Box
    print("\n--- Step 2: Black Box ---")
    await page.goto("https://members.helium10.com/black-box", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    print(f"Black Box URL: {page.url}")
    await page.screenshot(path="/app/data/debug/h10_blackbox.png")

    # Check page structure
    inputs = await page.evaluate("""() => {
        const els = document.querySelectorAll('input, textarea');
        return Array.from(els).slice(0, 20).map(el => ({
            type: el.type, name: el.name, id: el.id, 
            placeholder: el.placeholder.substring(0, 60),
            class: el.className.substring(0, 60),
            visible: el.offsetParent !== null
        }));
    }""")
    print("\nInputs on Black Box:")
    for inp in inputs:
        if inp.get("visible"):
            print(f"  {inp}")

    buttons = await page.evaluate("""() => {
        const els = document.querySelectorAll('button');
        return Array.from(els).slice(0, 15).map(el => ({
            text: el.textContent.trim().substring(0, 50),
            class: el.className.substring(0, 60),
            visible: el.offsetParent !== null
        }));
    }""")
    print("\nButtons:")
    for btn in buttons:
        if btn.get("visible"):
            print(f"  {btn}")

    await ctx.storage_state(path="/app/data/browser_state/helium10.json")
    await browser.close()
    await pw.stop()
    print("\nDone. Session saved.")

asyncio.run(main())
