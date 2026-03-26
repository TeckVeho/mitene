"""Remote browser session for NotebookLM web-based login.

Manages a headless Playwright browser on the server, streaming screenshots
and forwarding user input via WebSocket so end users can log in to Google
from the deployed web UI without SSH access.

Only one session is allowed at a time (singleton pattern).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from app.config import STORAGE_STATE

logger = logging.getLogger(__name__)

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/"
NOTEBOOKLM_HOST = "notebooklm.google.com"

# Viewport size for the headless browser
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800

# Screenshot settings
SCREENSHOT_INTERVAL = 0.3  # seconds between frames (~3 FPS, PNG is larger)


class RemoteBrowserSession:
    """Manages a single Playwright browser session for remote login."""

    def __init__(self) -> None:
        self._playwright = None
        self._context = None
        self._page = None
        self._running = False
        self._lock = asyncio.Lock()
        self._xvfb_proc: Optional[subprocess.Popen] = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start a new browser session navigated to NotebookLM."""
        async with self._lock:
            if self._running:
                raise RuntimeError("A remote login session is already running.")

            from playwright.async_api import async_playwright

            # Auto-start Xvfb virtual display if no $DISPLAY on headless servers
            if not os.environ.get("DISPLAY") and shutil.which("Xvfb"):
                display_num = "99"
                self._xvfb_proc = subprocess.Popen(
                    ["Xvfb", f":{display_num}", "-screen", "0", "1920x1080x24", "-ac"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                os.environ["DISPLAY"] = f":{display_num}"
                await asyncio.sleep(0.5)
                logger.info("Started Xvfb virtual display on :%s", display_num)

            self._playwright = await async_playwright().start()

            browser_profile = Path.home() / ".notebooklm" / "browser_profile"
            browser_profile.mkdir(parents=True, exist_ok=True, mode=0o700)

            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(browser_profile),
                headless=False,  # Google blocks headless login — must use headed mode
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--password-store=basic",
                    "--force-device-scale-factor=2",
                ],
                ignore_default_args=["--enable-automation"],
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                device_scale_factor=2,
            )

            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            await self._page.goto(NOTEBOOKLM_URL, wait_until="load")
            self._running = True
            logger.info("Remote browser session started, navigated to %s", NOTEBOOKLM_URL)

    async def get_screenshot(self) -> str:
        """Capture a JPEG screenshot and return as base64 string."""
        if not self._running or not self._page:
            raise RuntimeError("No active browser session.")

        screenshot_bytes = await self._page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode("ascii")

    async def send_mouse_click(self, x: float, y: float, button: str = "left") -> None:
        """Click at the given coordinates."""
        if not self._running or not self._page:
            return
        await self._page.mouse.click(x, y, button=button)

    async def send_mouse_move(self, x: float, y: float) -> None:
        """Move mouse to the given coordinates."""
        if not self._running or not self._page:
            return
        await self._page.mouse.move(x, y)

    async def send_keyboard_type(self, text: str) -> None:
        """Type text into the focused element."""
        if not self._running or not self._page:
            return
        await self._page.keyboard.type(text, delay=50)

    async def send_keyboard_press(self, key: str) -> None:
        """Press a special key (Enter, Tab, Backspace, etc.)."""
        if not self._running or not self._page:
            return
        await self._page.keyboard.press(key)

    async def save_and_close(self) -> str:
        """Save browser cookies to storage_state.json and close."""
        async with self._lock:
            if not self._running or not self._context:
                raise RuntimeError("No active browser session.")

            try:
                page = self._page
                if page:
                    # Navigate to ensure fresh cookies from Google domains
                    await page.goto(GOOGLE_ACCOUNTS_URL, wait_until="load")
                    await page.goto(NOTEBOOKLM_URL, wait_until="load")

                    current_url = page.url
                    if NOTEBOOKLM_HOST not in current_url:
                        logger.warning(
                            "Current URL is %s (not NotebookLM). Saving anyway.",
                            current_url,
                        )

                storage_path = STORAGE_STATE
                storage_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                await self._context.storage_state(path=str(storage_path))
                storage_path.chmod(0o600)

                logger.info("Auth saved to %s", storage_path)
                return str(storage_path)
            finally:
                await self._cleanup()

    async def cancel(self) -> None:
        """Close the browser without saving."""
        async with self._lock:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Internal cleanup — close browser and playwright."""
        try:
            if self._context:
                await self._context.close()
        except Exception as e:
            logger.warning("Error closing browser context: %s", e)
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning("Error stopping playwright: %s", e)
        # Stop Xvfb if we started it
        if self._xvfb_proc:
            try:
                self._xvfb_proc.terminate()
                self._xvfb_proc.wait(timeout=5)
                logger.info("Stopped Xvfb virtual display.")
            except Exception as e:
                logger.warning("Error stopping Xvfb: %s", e)
            self._xvfb_proc = None
            # Reset DISPLAY so next session re-creates Xvfb
            os.environ.pop("DISPLAY", None)
        self._context = None
        self._page = None
        self._playwright = None
        self._running = False
        logger.info("Remote browser session cleaned up.")


# Singleton session instance
_session: Optional[RemoteBrowserSession] = None
_session_lock = asyncio.Lock()


async def get_or_create_session() -> RemoteBrowserSession:
    """Get the singleton session, creating if needed."""
    global _session
    async with _session_lock:
        if _session is None or not _session.is_running:
            _session = RemoteBrowserSession()
        return _session
