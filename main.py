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
KEYWORDS = ["Phường Tương Mai", "Xã Xuân Giang", "Hà Nội"]

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

	browser = None

	try:

		async with async_playwright() as p:
			browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")

			if not browser.contexts:
				raise Exception("No browser context found from GPM")

			context = browser.contexts[0]
			# await context.route("**/*", block_resources)

			# Config từ MongoDB
			config = db.tiktok_bot_configs.find_one({"bot_name": settings.BOT_NAME})

			if not config:
				raise ValueError("Bot config not found")

			org_ids = config.get("org_id", [])
			org_ids_int = [int(x) for x in org_ids]

			keyword_col = db.keyword

			docs = list(keyword_col.find({
				"org_id": {"$in": org_ids_int}
			}))

			logger.info(f"Collection: {keyword_col.name}")
			logger.info(f"Total keywords: {len(docs)}")

			keywords = []

			for doc in docs:
				doc["_id"] = str(doc["_id"])
				keywords.append(doc["keyword"])

			await delay(1000, 2000)
			await crawl_tiktok_search_1(context, keywords, API_FILTERS)

	except Exception as e:
		logger.exception(f"Error in run_with_gpm(): {e}")

	finally:
		# Đóng browser nếu còn mở
		try:
			if browser:
				await browser.close()
		except:
			pass

		# Stop GPM profile
		try:
			requests.get(f"{GPM_API}/profiles/stop/{PROFILE_ID}")
			logger.info("GPM profile stopped")
		except Exception as e:
			logger.error(f"Failed to stop GPM profile: {e}")

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
		await crawl_tiktok_search_1(context, KEYWORDS, API_FILTERS)

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


async def random_view_video(page, locator):
    count = await locator.count()
    if count == 0:
        return

    if random.random() < 0.5:  # 50% khả năng click
        index = random.randint(0, min(count - 1, 5))
        await locator.nth(index).click()
        await page.wait_for_timeout(random.randint(4000, 8000))
        await page.go_back()
        await page.wait_for_timeout(random.randint(2000, 4000))

async def crawl_tiktok_search(context, KEYWORDS, API_FILTERS):

	page = await context.new_page()
	current_keyword = None
	videos_by_keyword = defaultdict(list)
	seen_ids_by_keyword = defaultdict(set)

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

	await page.goto("https://www.tiktok.com", timeout=60000)
	await page.wait_for_load_state("domcontentloaded")
	await page.wait_for_timeout(5000)

	for keyword in KEYWORDS:

		logger.info(f"Search keyword: {keyword}")

		current_keyword = keyword
		videos_by_keyword[keyword] = []
		seen_ids_by_keyword[keyword] = set()

		unix_time = int(time.time() * 1000)
		encoded = urllib.parse.quote(keyword)

		search_url = f"https://www.tiktok.com/search/video?q={encoded}&t={unix_time}"

		await page.goto(search_url, timeout=60000)
		await page.wait_for_timeout(8000)

		locator = page.locator("[id^='grid-item-container-']")

		await human_scroll(page, locator, times=random.randint(1, 4))

		await random_view_video(page=page, locator=locator)

		videos = videos_by_keyword[keyword]

		logger.info(f"Total Videos collected: {len(videos)}")

		results = []

		now_ts = int(time.time())
		days_ago = now_ts - 7 * 24 * 60 * 60  # 7 ngày tính theo giây

		for item in videos:
			try:
				pub_time = int(item.get("createTime", 0))

				if pub_time < days_ago:
					continue

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
				logger.error(f"Parse error: {e}")

		logger.info(f"Parsed {len(results)} posts")

		if results:
			try:
				result = await postToESUnclassified(results)
				logger.info(f"Posted {len(results)} posts to API MASTER: {result.get('status')}")
			except Exception as e:
				logger.error(f"Error posting to API MASTER: {e}")
		else:
			logger.info("No results to post")

		# reset keyword để tránh API call trễ
		current_keyword = None
		logger.info(f"⏳ Waiting before next keyword...")

		await delay(60000, 120000)

	logger.info("\n🎉 Done crawling all keywords")
	await page.close()








async def crawl_tiktok_search_1(context, KEYWORDS, API_FILTERS):

    videos_by_keyword = defaultdict(list)
    seen_ids_by_keyword = defaultdict(set)

    BATCH_MIN = 5
    BATCH_MAX = 10

    i = 0
    total = len(KEYWORDS)

    while i < total:

        batch_size = random.randint(BATCH_MIN, BATCH_MAX)
        batch_keywords = KEYWORDS[i:i+batch_size]

        logger.info(f"🚀 New session with {len(batch_keywords)} keywords")

        page = await context.new_page()
        current_keyword = None

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

                        if video_id not in seen_ids_by_keyword[current_keyword]:
                            seen_ids_by_keyword[current_keyword].add(video_id)
                            videos_by_keyword[current_keyword].append(item)

        page.on("response", on_response)

        await page.goto("https://www.tiktok.com", timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(random.randint(4000, 7000))

        for keyword in batch_keywords:

            logger.info(f"Search keyword: {keyword}")

            current_keyword = keyword
            videos_by_keyword[keyword] = []
            seen_ids_by_keyword[keyword] = set()

            unix_time = int(time.time() * 1000)
            encoded = urllib.parse.quote(keyword)
            search_url = f"https://www.tiktok.com/search/video?q={encoded}&t={unix_time}"

            await page.goto(search_url, timeout=60000)
            await page.wait_for_timeout(random.randint(6000, 9000))

            locator = page.locator("[id^='grid-item-container-']")

            await human_scroll(page, locator, times=random.randint(1, 4))
            await random_view_video(page, locator)

            videos = videos_by_keyword[keyword]
            logger.info(f"Total Videos collected: {len(videos)}")

            results = []
            now_ts = int(time.time())
            days_ago = now_ts - 7 * 24 * 60 * 60

            for item in videos:
                try:
                    pub_time = int(item.get("createTime", 0))
                    if pub_time < days_ago:
                        continue

                    video_info = {
                        "keyword": keyword,
                        "video_id": item.get("id"),
                        "description": item.get("desc"),
                        "pub_time": pub_time,
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
                    logger.error(f"Parse error: {e}")

            logger.info(f"Parsed {len(results)} posts")

            if results:
                try:
                    result = await postToESUnclassified(results)
                    logger.info(f"Posted {len(results)} posts to API MASTER: {result.get('status')}")
                except Exception as e:
                    logger.error(f"Error posting to API MASTER: {e}")

            current_keyword = None
            await asyncio.sleep(random.randint(60, 120))

        logger.info("🛑 Closing page for rest period")
        await page.close()

        rest_time = random.randint(180, 360)
        logger.info(f"😴 Resting {rest_time}s before next session")
        await asyncio.sleep(rest_time)

        i += batch_size

    logger.info("🎉 Done crawling all keywords")


async def schedule():
	MINUTE = settings.DELAY
	INTERVAL = MINUTE * 60
	while True:
		try:
			if settings.DEBUG:
				await run_test_1()
			else:
				await run_with_gpm()

			logger.info(f"=== Run completed. Sleeping for {MINUTE} minutes ===")
		except Exception as e:
			logger.exception("Unhandled exception in run()")

		await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
	asyncio.run(schedule())