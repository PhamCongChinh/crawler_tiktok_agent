import asyncio
from playwright.async_api import async_playwright

from src.scrapers.search import crawl_tiktok_search
from src.config.logging import setup_logging
from src.config.settings import settings
import logging

setup_logging()
logger = logging.getLogger(__name__)

KEYWORDS = ["Xã Xuân Giang", "Hà Nội"]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(storage_state="tiktok_profile.json")
        logger.info(f"[{settings.BOT_NAME}] Running test crawl...")
        await crawl_tiktok_search(context, KEYWORDS, settings.BOT_NAME)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
