import asyncio
import requests
from playwright.async_api import async_playwright
from db.mongo import MongoDB
from src.crawler_keywords import CrawlerKeyword
from src.crawlers.keyword_crawler import KeywordCrawler
from src.crawlers.video_crawler import VideoCrawler
from src.services.page_manager import PageManager
from src.services.redis_dedup import RedisDedupService
from src.config.redis_client import redis_client
from src.config.logging import setup_logging
import logging


from src.utils import delay, in_quiet_hours, seconds_until_quiet_end
setup_logging()
logger = logging.getLogger(__name__)
import json

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
			await delay(800, 1500)
			await page.goto("https://www.tiktok.com", timeout=60000)
			logger.info("Đã vào TikTok bằng GPM profile")

			db = MongoDB.get_db()
			keyword_col = db.keyword

			logger.info(f"Collection: {keyword_col.name}")
			logger.info(f"Total docs: {keyword_col.count_documents({})}")

			docs = keyword_col.find({
				"org_id": {"$in": [2]}
			})

			keywords = []

			for doc in docs:
				doc["_id"] = str(doc["_id"])  # nếu cần
				keywords.append(doc["keyword"])
			
			await delay(1000, 2000)

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

			# with open("keywords.json", "r", encoding="utf8") as f:
			# 	keywords = json.load(f)
			
			db = MongoDB.get_db()
			keyword_col = db.keyword

			logger.info(f"Collection: {keyword_col.name}")
			logger.info(f"Total docs: {keyword_col.count_documents({})}")

			docs = keyword_col.find({
				"org_id": {"$in": [2,236282]}
			})

			keywords = []

			for doc in docs:
				doc["_id"] = str(doc["_id"])  # nếu cần
				keywords.append(doc["keyword"])


			await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)

		finally:
			await page.close()
			await browser.close()

	

async def schedule():
	MINUTE = settings.DELAY
	INTERVAL = MINUTE * 60
	while True:
		if in_quiet_hours(settings.QUIET_HOURS_START, settings.QUIET_HOURS_END):
			sleep_sec = seconds_until_quiet_end(
				settings.QUIET_HOURS_START,
				settings.QUIET_HOURS_END
			)
			logger.info(f"⏸ Nghỉ crawl tới {settings.QUIET_HOURS_END}:00 "
						f"(ngủ {sleep_sec // 60} phút)")
			await asyncio.sleep(sleep_sec)
			continue

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