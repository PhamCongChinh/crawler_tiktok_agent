import asyncio
from datetime import datetime, timezone
import random
import json
import time
import requests
from playwright.async_api import async_playwright
import urllib
from src.api import postToESUnclassified
from src.parsers.video_parser import TiktokPost
from src.db.mongo import MongoDB
from src.crawler_keywords import CrawlerKeyword
from src.config.logging import setup_logging
import logging
from collections import defaultdict

from src.utils import delay
setup_logging()
logger = logging.getLogger(__name__)

from src.config.settings import settings

# GPM_API = settings.GPM_API
# PROFILE_ID = settings.PROFILE_ID

TIKTOK_URL = "https://www.tiktok.com"
KEYWORDS = ["python"]

# API TikTok cần bắt
API_FILTERS = [
	"/api/search",
	"/api/post",
	"/api/item_list",
	"/api/recommend"
]

SEARCH_API = "/api/search/general/full/"

db = MongoDB.get_db()
bot_config = db.tiktok_bot_configs

async def block_resources(route, request):
	if request.resource_type in ("image", "font"):
		await route.abort()
	else:
		await route.continue_()

async def human_delay(min_ms=800, max_ms=1500):
	await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

async def run_with_gpm():
	
	GPM_API = bot_config.find_one({"bot_name": f"{settings.BOT_NAME}"}).get("gpm_api")
	PROFILE_ID = bot_config.find_one({"bot_name": f"{settings.BOT_NAME}"}).get("profile_id")

	resp = requests.get(f"{GPM_API}/profiles/start/{PROFILE_ID}")
	resp.raise_for_status()
	data = resp.json()["data"]
	debug_addr = data["remote_debugging_address"]

	async with async_playwright() as p:
		browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")

		context = browser.contexts[0]
		await context.route("**/*", block_resources)

		page = await context.new_page()

		# items = []

		# # Bắt response XHR
		# async def handle_response(response):
		# 	if SEARCH_API in response.url and response.request.method == "GET":
		# 		try:
		# 			json_data = await response.json()
		# 			for row in json_data.get("data", []):
		# 				if row.get("type") == 1 and "item" in row:
		# 					items.append(row["item"])
		# 		except Exception as e:
		# 			print("❌ Parse error:", e)

		# page.on("response", handle_response)
		
		try:
			await delay(800, 1500)
			await page.goto("https://www.tiktok.com", timeout=60000)
			logger.info("Đã vào TikTok bằng GPM profile")

			# Config từ MongoDB
			config = db.tiktok_bot_configs.find_one({"bot_name": f"{settings.BOT_NAME}"})
			org_ids = config.get("org_id")
			org_ids_int = [int(x) for x in org_ids]


			# db = MongoDB.get_db()
			keyword_col = db.keyword

			logger.info(f"Collection: {keyword_col.name}")
			logger.info(f"Total docs: {keyword_col.count_documents({})}")

			docs = keyword_col.find({
				"org_id": {"$in": org_ids_int}
			})

			keywords = []

			for doc in docs:
				doc["_id"] = str(doc["_id"])
				keywords.append(doc["keyword"])
			
			await delay(1000, 2000)

			for idx, keyword in enumerate(keywords, start=1):
				logger.info(f"🔍 Bắt đầu crawl keyword {idx}/{len(keywords)}: {keyword}")

				items = []

				# Bắt response XHR
				async def handle_response(response):
					if SEARCH_API in response.url and response.request.method == "GET":
						try:
							json_data = await response.json()
							for row in json_data.get("data", []):
								if row.get("type") == 1 and "item" in row:
									items.append(row["item"])
						except Exception as e:
							print("❌ Parse error:", e)

				page.on("response", handle_response)

				print(f"🔍 Search keyword: {keyword}")

				search_btn = page.locator('button[data-e2e="nav-search"]')
				await search_btn.wait_for(state="visible", timeout=15000)
				await human_delay(1500, 2500)
				await search_btn.click()
				print("Clicked search button")
				await human_delay(1500, 2500)

				# search_input = page.locator(
				# 	'input[data-e2e="search-user-input"]:visible'
				# ).first
				search_input = page.locator(
					'form[data-e2e="search-box"] input[data-e2e="search-user-input"]:visible'
				).first
				print("Got search input")
				await search_input.click()

				await human_delay(500, 1000)
				await page.keyboard.type(keyword, delay=120)
				await human_delay(500, 1000)
				await page.keyboard.press("Enter")
				await page.wait_for_timeout(5000)


				print(f"✅ Got {len(items)} items")
				results = []
				for item in data:
					video_info = {
						"video_id": item.get("id"),
						"description": item.get("desc"),
						"pub_time": int(item.get("createTime")),
						"unique_id": item.get("author", {}).get("uniqueId", ""),
						"auth_id": item.get("author", {}).get("id", 0),
						"auth_name": item.get("author", {}).get("nickname", ""),
						"comments": item.get("stats", {}).get("commentCount", 0),
						"shares": item.get("stats", {}).get("shareCount", 0),
						"reactions": item.get("stats", {}).get("diggCount", 0),
						"favors": item.get("stats", {}).get("collectCount", 0),
						"views": item.get("stats", {}).get("playCount", 0)
					}

					data = TiktokPost().new(video_info)
					results.append(data)

				print(f"✅ Parsed {len(results)} posts, posting to ES...")
				print("Sample post:", results[:3])

				try:
					result = await postToESUnclassified(results)
					print("✅ Posted to ES:", result)
				except Exception as e:
					print("❌ Error posting to ES:", e)



				await human_delay(10000, 20000)


			# await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)
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

		# await delay(800, 1500)
		# try:
		# 	# await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=60000)
		# 	logger.info("Đã vào trang chủ TikTok")

		# 	# db = MongoDB.get_db()
		# 	config = db.tiktok_bot_configs.find_one({"bot_name": f"{settings.BOT_NAME}"})
		# 	org_ids = config.get("org_id")

		# 	print("Keywords to crawl:", org_ids)

		# 	org_ids_int = [int(x) for x in org_ids]

		# 	print("Org IDs as integers:", org_ids_int)

		# 	keyword_col = db.keyword

		# 	logger.info(f"Collection: {keyword_col.name}")
		# 	logger.info(f"Total docs: {keyword_col.count_documents({})}")

		# 	docs = keyword_col.find({
		# 		"org_id": {"$in": org_ids_int}
		# 	})

		# 	keywords = []

		# 	for doc in docs:
		# 		doc["_id"] = str(doc["_id"])
		# 		keywords.append(doc["keyword"])

		# 	await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)

		# finally:
		# 	await page.close()
		# 	await browser.close()




async def run_test_1():
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
		# ======================
		# XHR COLLECTOR
		# ======================
		xhr_calls = defaultdict(dict)

		async def on_request(req):
			if any(api in req.url for api in API_FILTERS):
				xhr_calls[req.url]["request"] = {
					"method": req.method,
					"headers": req.headers,
					"payload": req.post_data,
					"timestamp": datetime.now(timezone.utc).isoformat()
				}

		async def on_response(res):
			if any(api in res.url for api in API_FILTERS):
				try:
					body = await res.json()
				except:
					body = None

				xhr_calls[res.url]["response"] = {
					"status": res.status,
					"headers": res.headers,
					"body": body,
					"timestamp": datetime.now(timezone.utc).isoformat()
				}

		page.on("request", on_request)
		page.on("response", on_response)

		# ======================
		# OPEN TIKTOK
		# ======================
		print("🚀 Open TikTok")
		await page.goto(TIKTOK_URL, timeout=60000)
		await page.wait_for_load_state("networkidle")
		await human_delay()

		# ======================
		# SEARCH LOOP
		# ======================
		for keyword in KEYWORDS:
			print(f"🔍 Search keyword: {keyword}")

			unix_time = int(time.time())
			encoded = urllib.parse.quote(keyword)

			search_url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"
			await page.goto(search_url, timeout=60000)

			await page.wait_for_timeout(8000)
			await human_delay(1500, 2500)

		# ======================
		# SAVE RESULT
		# ======================
		with open("xhr_calls1.json", "w", encoding="utf-8") as f:
			json.dump(xhr_calls, f, ensure_ascii=False, indent=2)

		print(f"✅ Done. Captured {len(xhr_calls)} API calls")



async def schedule():
	MINUTE = settings.DELAY
	INTERVAL = MINUTE * 60
	while True:
		try:
			if settings.DEBUG:
				await run_test_1()
			else:
				await run_with_gpm()

			logger.info(f"=== Hoàn thành, chờ {MINUTE} phút ===")
		except Exception as e:
			logger.error(f"Lỗi trong run(): {e}")

		await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
	asyncio.run(schedule())