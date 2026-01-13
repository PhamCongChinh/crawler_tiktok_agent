import asyncio
import requests
from playwright.async_api import async_playwright
from src.config.logging import setup_logging
import logging

from src.utils import delay
setup_logging()
logger = logging.getLogger(__name__)
import json

from src.crawler_keywords import CrawlerKeyword
from src.config.settings import settings

GPM_API = settings.GPM_API
PROFILE_ID = settings.PROFILE_ID

async def block_resources(route, request):
	if request.resource_type in ("image", "font"):
		await route.abort()
	else:
		await route.continue_()

async def run_with_gpm():
	resp = requests.get(f"{GPM_API}/profiles/start/{PROFILE_ID}")
	resp.raise_for_status()
	data = resp.json()["data"]
	debug_addr = data["remote_debugging_address"]

	async with async_playwright() as p:
		browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")

		context = browser.contexts[0]
		await context.route("**/*", block_resources)

		page = await context.new_page()

		try:
			await page.goto("https://www.tiktok.com", timeout=60000)
			logger.info("Đã vào TikTok bằng GPM profile")
			with open("keywords.json", "r", encoding="utf8") as f:
				keywords = json.load(f)
			await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)
		finally:
			await page.close()
			await browser.close()


async def run_test():
	async with async_playwright() as p:
		chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"  # đường dẫn Chrome trên Windows

		browser = await p.chromium.launch(
			headless=False,
			executable_path=chrome_path,
			args=["--disable-blink-features=AutomationControlled"]
		)
		context = await browser.new_context(storage_state="tiktok_profile.json")

		await context.route("**/*", block_resources)

		page = await context.new_page()
		await delay(800, 1500)
		try:
			await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=60000)
			logger.info("Đã vào trang chủ TikTok")

			with open("keywords.json", "r", encoding="utf8") as f:
				keywords = json.load(f)

			await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)
		finally:
			await page.close()
			await browser.close()

	

async def schedule():
	MINUTE = settings.DELAY
	INTERVAL = MINUTE * 60
	while True:
		logger.info("---------------Bắt đầu chạy run() -----------------")
		try:
			if settings.DEBUG:
				await run_test()
			else:
				await run_with_gpm()
			
			logger.info(f"=== Hoàn thành, chờ {MINUTE} phút ===")
		except Exception as e:
			logger.error(f"Lỗi trong run(): {e}")

		await asyncio.sleep(INTERVAL)

if __name__ == "__main__":
	asyncio.run(schedule())