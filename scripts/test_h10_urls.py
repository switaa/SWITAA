"""Find the correct Helium 10 login URL."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    page = await browser.new_page()

    urls_to_try = [
        "https://members.helium10.com/",
        "https://www.helium10.com/login",
        "https://www.helium10.com/sign-in",
        "https://members.helium10.com/user/signin",
        "https://members.helium10.com/signin",
    ]

    for url in urls_to_try:
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            final = page.url
            status = resp.status if resp else "no response"
            print(f"{url} -> {final} (status: {status})")
        except Exception as e:
            print(f"{url} -> ERROR: {e}")

    # Try the main page and look for login links
    await page.goto("https://www.helium10.com/", wait_until="domcontentloaded", timeout=15000)
    print(f"\nMain page final URL: {page.url}")
    
    # Check for login-related links
    links = await page.evaluate("""() => {
        const anchors = document.querySelectorAll('a');
        return Array.from(anchors)
            .filter(a => a.href && (a.href.includes('login') || a.href.includes('sign') || a.textContent.toLowerCase().includes('log in') || a.textContent.toLowerCase().includes('sign in')))
            .map(a => ({href: a.href, text: a.textContent.trim()}));
    }""")
    print("Login links found:", links)

    await browser.close()
    await pw.stop()

asyncio.run(main())
