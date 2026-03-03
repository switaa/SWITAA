from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from marcus.config.settings import BROWSER_STATE_DIR


class BrowserManager:
    """Manages Playwright browser lifecycle with persistent sessions."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: dict[str, BrowserContext] = {}

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

    async def get_context(self, name: str) -> BrowserContext:
        """Get or create a named browser context with persistent storage."""
        if name in self._contexts:
            return self._contexts[name]

        state_path = BROWSER_STATE_DIR / f"{name}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        storage_state = str(state_path) if state_path.exists() else None

        context = await self._browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self._contexts[name] = context
        return context

    async def save_context(self, name: str):
        """Persist cookies/storage for a named context."""
        if name not in self._contexts:
            return
        state_path = BROWSER_STATE_DIR / f"{name}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        await self._contexts[name].storage_state(path=str(state_path))

    async def new_page(self, context_name: str) -> Page:
        context = await self.get_context(context_name)
        page = await context.new_page()
        await _apply_stealth(page)
        return page

    async def close(self):
        for name in list(self._contexts):
            await self.save_context(name)
            await self._contexts[name].close()
        self._contexts.clear()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


async def _apply_stealth(page: Page):
    """Minimal stealth tweaks to reduce bot detection."""
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en'] });
    """)
