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
KEYWORDS = ["Phường Ba Đình","Phường Bạch Mai"]

# API TikTok cần bắt
# API_FILTERS = [
# 	"/api/search",
# 	"/api/post",
# 	"/api/item_list",
# 	"/api/recommend"
# ]

API_FILTERS = [
	"/api/search/item/full/",
]

SEARCH_API = "/api/search/item/full/"

db = MongoDB.get_db()
bot_config = db.tiktok_bot_configs


async def human_scroll(page, locator, times: int = 1):
		"""
		Scroll giống hành vi người dùng thật
		:param page: playwright page
		:param locator: locator video items
		:param times: số lần scroll
		"""
		for i in range(times):
			count = await locator.count()
			if count == 0:
				break

			# Move mouse nhẹ (giống người)
			await page.mouse.move(
				random.randint(200, 600),
				random.randint(200, 500)
			)

			# Scroll tới item cuối
			await locator.nth(count - 1).scroll_into_view_if_needed()

			# dừng xem ngắn
			await page.wait_for_timeout(random.randint(800, 1500))

			# 🔄 20% scroll ngược lại
			if random.random() < 0.2:
				await page.mouse.wheel(0, -random.randint(150, 300))
				await page.wait_for_timeout(random.randint(200, 400))

			# 😵‍💫 10% đứng im rất lâu (lướt mà quên scroll)
			if random.random() < 0.1:
				long_pause = random.randint(6000, 12000)
				await page.wait_for_timeout(long_pause)

			# Người dùng thường dừng xem
			await page.wait_for_timeout(random.randint(700, 1200))

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

	# ===== START PROFILE =====
	resp = requests.get(f"{GPM_API}/profiles/start/{PROFILE_ID}")
	resp.raise_for_status()

	data = resp.json()["data"]
	debug_addr = data["remote_debugging_address"]

	async with async_playwright() as p:
		browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")

		if not browser.contexts:
			raise Exception("❌ No browser context found from GPM")

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

			keywords_count = [doc["keyword"] for doc in docs]
			logger.info(f"Total keywords: {len(keywords_count)}")

			keywords = []

			for doc in docs:
				doc["_id"] = str(doc["_id"])
				keywords.append(doc["keyword"])
			
			await delay(1000, 2000)

			await crawl_tiktok_search(context, keywords, API_FILTERS)

			# search_btn = page.locator('button[data-e2e="nav-search"]')
			# await search_btn.wait_for(state="visible", timeout=15000)
			# await human_delay(1500, 2500)
			# await search_btn.click()
			# await human_delay(1500, 2500)

			# search_input = page.locator(
			# 	'form[data-e2e="search-box"] input[data-e2e="search-user-input"]:visible'
			# ).first

			# # await search_input.wait_for(state="visible", timeout=15000)

			# for idx, keyword in enumerate(keywords, start=1):
			# 	logger.info(f"🔍 Bắt đầu crawl keyword {idx}/{len(keywords)}: {keyword}")

			# 	print(f"🔍 Search keyword: {keyword}")

			# 	items.clear()
			# 	await search_input.click()

			# 	 # clear old text
			# 	await page.keyboard.press("Control+A")
			# 	await page.keyboard.press("Backspace")

			# 	await human_delay(500, 1000)
			# 	await page.keyboard.type(keyword, delay=120)
			# 	await human_delay(500, 1000)
			# 	await page.keyboard.press("Enter")
			# 	await page.wait_for_timeout(6000)


			# 	print(f"✅ Got {len(items)} items")

			# 	if not items:
			# 		continue

			# 	results = []
			# 	for item in items:
			# 		video_info = {
			# 			"video_id": item.get("id"),
			# 			"description": item.get("desc"),
			# 			"pub_time": int(item.get("createTime")),
			# 			"unique_id": item.get("author", {}).get("uniqueId", ""),
			# 			"auth_id": item.get("author", {}).get("id", 0),
			# 			"auth_name": item.get("author", {}).get("nickname", ""),
			# 			"comments": item.get("stats", {}).get("commentCount", 0),
			# 			"shares": item.get("stats", {}).get("shareCount", 0),
			# 			"reactions": item.get("stats", {}).get("diggCount", 0),
			# 			"favors": item.get("stats", {}).get("collectCount", 0),
			# 			"views": item.get("stats", {}).get("playCount", 0)
			# 		}

			# 		data = TiktokPost().new(video_info)
			# 		results.append(data)

			# 	print(f"✅ Parsed {len(results)} posts, posting to ES...")
			# 	print("Sample post:", results[:3])

			# 	try:
			# 		result = await postToESUnclassified(results)
			# 		print("✅ Posted to ES:", result)
			# 	except Exception as e:
			# 		print("❌ Error posting to ES:", e)

			# 	await human_delay(10000, 20000)


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
		await crawl_tiktok_search(context, KEYWORDS, API_FILTERS)

		# page = await context.new_page()
		# # ======================
		# # XHR COLLECTOR
		# # ======================
		# xhr_calls = defaultdict(dict)

		# videos = []
		
		# async def on_request(req):
		# 	if any(api in req.url for api in API_FILTERS):
		# 		xhr_calls[req.url]["request"] = {
		# 			"method": req.method,
		# 			"headers": req.headers,
		# 			"payload": req.post_data,
		# 			"timestamp": datetime.now(timezone.utc).isoformat()
		# 		}

		# async def on_response(res):
		# 	if any(api in res.url for api in API_FILTERS):
		# 		try:
		# 			body = await res.json()
		# 		except:
		# 			body = None

		# 		xhr_calls[res.url]["response"] = {
		# 			"status": res.status,
		# 			"headers": res.headers,
		# 			"body": body,
		# 			"timestamp": datetime.now(timezone.utc).isoformat()
		# 		}

		# 		if body and body.get("status_code") == 0:
		# 			items = body.get("item_list", [])
		# 			videos.extend(items)

		# page.on("request", on_request)
		# page.on("response", on_response)

		# # ======================
		# # OPEN TIKTOK
		# # ======================
		# print("🚀 Open TikTok")
		# await page.goto(TIKTOK_URL, timeout=60000)
		# await page.wait_for_load_state("domcontentloaded")
		# await human_delay()

		# # ======================
		# # SEARCH LOOP
		# # ======================
		# for keyword in KEYWORDS:
		# 	print(f"🔍 Search keyword: {keyword}")

		# 	unix_time = int(time.time())
		# 	encoded = urllib.parse.quote(keyword)

		# 	search_url = f"https://www.tiktok.com/search/video?q={encoded}&t={unix_time}"
		# 	await page.goto(search_url, timeout=60000)

		# 	await page.wait_for_timeout(8000)
		# 	locator = page.locator("[id^='grid-item-container-']")

		# 	await human_scroll(page, locator, times=2)
		# 	await human_delay(1500, 2500)

		# # ======================
		# # SAVE RESULT
		# # ======================

		# print("Total Videos:", len(videos))


		# results = []
		# for item in videos:
		# 	video_info = {
		# 		"video_id": item.get("id"),
		# 		"description": item.get("desc"),
		# 		"pub_time": int(item.get("createTime")),
		# 		"unique_id": item.get("author", {}).get("uniqueId", ""),
		# 		"auth_id": item.get("author", {}).get("id", 0),
		# 		"auth_name": item.get("author", {}).get("nickname", ""),
		# 		"comments": item.get("stats", {}).get("commentCount", 0),
		# 		"shares": item.get("stats", {}).get("shareCount", 0),
		# 		"reactions": item.get("stats", {}).get("diggCount", 0),
		# 		"favors": item.get("stats", {}).get("collectCount", 0),
		# 		"views": item.get("stats", {}).get("playCount", 0)
		# 	}

		# 	data = TiktokPost().new(video_info)
		# 	results.append(data)

		# print(f"✅ Parsed {len(results)} posts, posting to ES...")

		# with open("xhr_calls3.json", "w", encoding="utf-8") as f:
		# 	json.dump(results, f, ensure_ascii=False, indent=2)

		# try:
		# 	result = await postToESUnclassified(results)
		# 	print("✅ Posted to ES:", result)
		# except Exception as e:
		# 	print("❌ Error posting to ES:", e)

		# await human_delay(10000, 20000)

###################
async def crawl_tiktok_search(context, KEYWORDS, API_FILTERS):

	page = await context.new_page()

	# ==========================
	# GLOBAL STATE
	# ==========================
	current_keyword = None
	videos_by_keyword = defaultdict(list)
	seen_ids_by_keyword = defaultdict(set)

	# ==========================
	# HUMAN SCROLL
	# ==========================
	async def human_scroll(page, max_scroll=10):
		last_count = 0

		for i in range(max_scroll):
			await page.mouse.wheel(0, random.randint(3000, 6000))
			await page.wait_for_timeout(random.randint(2000, 3500))

			if current_keyword:
				current_count = len(videos_by_keyword[current_keyword])

				# nếu không tăng video nữa → stop
				if current_count == last_count:
					print("🛑 No new videos, stop scrolling")
					break

				last_count = current_count

	# ==========================
	# RESPONSE HANDLER
	# ==========================
	async def on_response(res):
		nonlocal current_keyword

		if not current_keyword:
			return

		if any(api in res.url for api in API_FILTERS):

			try:
				body = await res.json()
			except:
				return

			if not body:
				return

			if body.get("status_code") == 0:
				items = body.get("item_list", [])

				for item in items:
					video_id = item.get("id")

					if not video_id:
						continue

					# chống duplicate
					if video_id not in seen_ids_by_keyword[current_keyword]:
						seen_ids_by_keyword[current_keyword].add(video_id)
						videos_by_keyword[current_keyword].append(item)

	page.on("response", on_response)

	# ==========================
	# OPEN TIKTOK HOME
	# ==========================
	print("🚀 Open TikTok")
	await page.goto("https://www.tiktok.com", timeout=60000)
	await page.wait_for_load_state("domcontentloaded")
	await page.wait_for_timeout(5000)

	# ==========================
	# KEYWORD LOOP
	# ==========================
	for keyword in KEYWORDS:

		print(f"\n==============================")
		print(f"🔍 Search keyword: {keyword}")
		print(f"==============================")

		current_keyword = keyword
		videos_by_keyword[keyword] = []
		seen_ids_by_keyword[keyword] = set()

		unix_time = int(time.time() * 1000)
		encoded = urllib.parse.quote(keyword)

		search_url = f"https://www.tiktok.com/search/video?q={encoded}&t={unix_time}"

		await page.goto(search_url, timeout=60000)
		await page.wait_for_timeout(8000)

		# scroll để load thêm video
		await human_scroll(page, max_scroll=8)

		videos = videos_by_keyword[keyword]

		print(f"📦 Total Videos collected: {len(videos)}")

		# ==========================
		# PARSE DATA
		# ==========================
		results = []

		for item in videos:
			try:
				video_info = {
					"keyword": keyword,
					"video_id": item.get("id"),
					"description": item.get("desc"),
					"pub_time": int(item.get("createTime", 0)),
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

			except Exception as e:
				print("❌ Parse error:", e)

		print(f"✅ Parsed {len(results)} posts")

		# ==========================
		# POST TO ES
		# ==========================
		with open(f"xhr_calls_{keyword}.json", "w", encoding="utf-8") as f:
			json.dump(results, f, ensure_ascii=False, indent=2)

		if results:
			try:
				result = await postToESUnclassified(results)
				print(f"🚀 Posted {len(results)} posts to ES")
				print(result)
			except Exception as e:
				print("❌ Error posting to ES:", e)
		else:
			print("⚠️ No results to post")

		# reset keyword để tránh API call trễ
		current_keyword = None

		await delay(10000, 20000)

	print("\n🎉 Done crawling all keywords")

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