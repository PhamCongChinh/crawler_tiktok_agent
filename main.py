import asyncio
import random
import time
import requests
import urllib
import logging
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

from src.parsers.comment_parser import TiktokComment
from src.api import postToESClassified, postToESUnclassified
from src.parsers.video_parser import TiktokPost
from src.db.mongo import MongoDB
from src.config.logging import setup_logging
from src.utils.scroll_utils import human_scroll
from src.utils.delay_utils import delay
from src.utils.browser_actions import random_view_video
from src.utils.sleep_manager import SleepManager
from src.heartbeat import heartbeat_loop
from src.config.settings import settings


setup_logging()
logger = logging.getLogger(__name__)

TIKTOK_URL = "https://www.tiktok.com"
KEYWORDS = ["Xã Xuân Giang", "Hà Nội"]

API_FILTERS = [
	"/api/search/item/full/",
]
API_COMMENT = [
	"/api/comment/list/",
]

GOTO_TIMEOUT = 60000   # ms
MAX_RETRIES   = 3

db = MongoDB.get_db()
bot_config = db.tiktok_bot_configs


async def run_with_gpm(bot_type: str, bot_name: str):

	# Chỉ query MongoDB 1 lần
	config = bot_config.find_one({"bot_name": bot_name})
	if not config:
		raise ValueError(f"Bot config not found for {bot_name}")

	GPM_API    = config.get("gpm_api")
	PROFILE_ID = config.get("profile_id")

	# ===== START PROFILE =====
	resp = requests.get(f"{GPM_API}/profiles/start/{PROFILE_ID}")
	resp.raise_for_status()

	debug_addr = resp.json()["data"]["remote_debugging_address"]
	browser = None

	try:
		async with async_playwright() as p:
			browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")

			if not browser.contexts:
				raise Exception("No browser context found from GPM")

			context = browser.contexts[0]

			org_ids     = config.get("org_id", [])
			org_ids_int = [int(x) for x in org_ids]

			keyword_col = db.keyword
			docs        = list(keyword_col.find({"org_id": {"$in": org_ids_int}}))

			logger.info(f"[{bot_name}] Collection: {keyword_col.name}")
			logger.info(f"[{bot_name}] Total keywords: {len(docs)}")

			keywords = [doc["keyword"] for doc in docs]

			await delay(1000, 2000)
			await crawl_tiktok_search(browser, context, keywords, API_FILTERS, bot_name)

	except Exception as e:
		logger.exception(f"Error in run_with_gpm(): {e}")

	finally:
		try:
			if browser:
				await browser.close()
		except Exception:
			pass

		try:
			requests.get(f"{GPM_API}/profiles/close/{PROFILE_ID}")
			logger.info("GPM profile stopped")
		except Exception as e:
			logger.error(f"Failed to stop GPM profile: {e}")


async def run_test(bot_type: str, bot_name: str):
	async with async_playwright() as p:
		chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
		browser = await p.chromium.launch(
			headless=False,
			executable_path=chrome_path,
			args=["--disable-blink-features=AutomationControlled"]
		)
		context = await browser.new_context(storage_state="tiktok_profile.json")

		if bot_type == "comment":
			logger.info("Crawl COMMENT")
			# await crawl_tiktok_comment(context=context)
		elif bot_type == "video":
			logger.info("Crawl VIDEO")
			await crawl_tiktok_search(browser, context, KEYWORDS, API_FILTERS, bot_name)
		else:
			await browser.close()


async def _goto_with_retry(page, url: str, bot_name: str, label: str) -> bool:
	"""Navigate đến url, retry tối đa MAX_RETRIES lần. Trả về True nếu thành công."""
	for attempt in range(1, MAX_RETRIES + 1):
		try:
			await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)
			return True
		except Exception as e:
			logger.warning(f"[{bot_name}] [{label}] goto attempt {attempt}/{MAX_RETRIES} failed: {e}")
			if attempt < MAX_RETRIES:
				await asyncio.sleep(random.randint(5, 10))
	logger.error(f"[{bot_name}] [{label}] All goto attempts failed, skipping")
	return False


async def crawl_tiktok_search(browser, context, KEYWORDS, API_FILTERS, bot_name):

	videos_by_keyword   = defaultdict(list)
	seen_ids_by_keyword = defaultdict(set)

	BATCH_MIN = 5
	BATCH_MAX = 10

	i     = 0
	total = len(KEYWORDS)

	while i < total:

		batch_size     = random.randint(BATCH_MIN, BATCH_MAX)
		batch_keywords = KEYWORDS[i:i + batch_size]

		logger.info(f"[{bot_name}] 🚀 New session with {len(batch_keywords)} keywords")

		page            = await context.new_page()
		current_keyword = None

		# Tính days_ago 1 lần cho cả batch
		days_ago = int(time.time()) - 7 * 24 * 60 * 60

		async def on_response(res):
			nonlocal current_keyword
			if not current_keyword:
				return
			if not any(api in res.url for api in API_FILTERS):
				return
			try:
				body = await res.json()
			except Exception:
				return
			if not body or body.get("status_code") != 0:
				return
			for item in body.get("item_list", []):
				video_id = item.get("id")
				if not video_id:
					continue
				if video_id not in seen_ids_by_keyword[current_keyword]:
					seen_ids_by_keyword[current_keyword].add(video_id)
					videos_by_keyword[current_keyword].append(item)

		page.on("response", on_response)

		# Load homepage
		homepage_ok = await _goto_with_retry(page, TIKTOK_URL, bot_name, "homepage")
		if not homepage_ok:
			await page.close()
			await asyncio.sleep(random.randint(30, 60))
			i += batch_size
			continue

		await page.wait_for_load_state("domcontentloaded")
		await page.wait_for_timeout(random.randint(4000, 7000))
		await page.mouse.move(
			random.randint(100, 900),
			random.randint(100, 600),
			steps=random.randint(10, 30)
		)
		await page.wait_for_timeout(random.randint(500, 1500))

		for keyword in batch_keywords:

			logger.info(f"[{bot_name}] [{keyword}] Search keyword: {keyword}")

			current_keyword                    = keyword
			videos_by_keyword[keyword]         = []
			seen_ids_by_keyword[keyword]       = set()

			unix_time  = int(time.time() * 1000)
			encoded    = urllib.parse.quote(keyword)
			search_url = f"{TIKTOK_URL}/search/video?q={encoded}&t={unix_time}"

			if not await _goto_with_retry(page, search_url, bot_name, keyword):
				current_keyword = None
				continue

			await page.wait_for_timeout(random.randint(6000, 9000))

			locator = page.locator("[id^='grid-item-container-']")
			await human_scroll(page, locator, times=random.randint(1, 4))
			await random_view_video(page)

			videos = videos_by_keyword[keyword]
			logger.info(f"[{bot_name}] [{keyword}] Total videos collected: {len(videos)}")

			results = []
			for item in videos:
				try:
					pub_time = int(item.get("createTime", 0))
					if pub_time < days_ago:
						continue

					video_info = {
						"keyword":     keyword,
						"video_id":    item.get("id"),
						"description": item.get("desc"),
						"pub_time":    pub_time,
						"unique_id":   item.get("author", {}).get("uniqueId", ""),
						"auth_id":     item.get("author", {}).get("id", 0),
						"auth_name":   item.get("author", {}).get("nickname", ""),
						"comments":    item.get("stats", {}).get("commentCount", 0),
						"shares":      item.get("stats", {}).get("shareCount", 0),
						"reactions":   item.get("stats", {}).get("diggCount", 0),
						"favors":      item.get("stats", {}).get("collectCount", 0),
						"views":       item.get("stats", {}).get("playCount", 0),
					}

					data = TiktokPost().new(video_info)
					results.append(data)

				except Exception as e:
					logger.error(f"[{bot_name}] [{keyword}] Parse error: {e}")

			if results:
				try:
					result = await postToESUnclassified(results)
					logger.info(f"[{bot_name}] [{keyword}] Posted {len(results)} posts to API MASTER: {result.get('status')}")
				except Exception as e:
					logger.error(f"[{bot_name}] [{keyword}] Error posting to API MASTER: {e}")

			current_keyword = None
			time_sleep = random.randint(60, 120)
			logger.info(f"[{bot_name}] Waiting {time_sleep}s for the next keyword ...")
			await asyncio.sleep(time_sleep)

		logger.info(f"[{bot_name}] 🛑 Closing page for rest period")
		await page.close()

		rest_time = random.randint(600, 900)
		logger.info(f"[{bot_name}] 😴 Resting {rest_time}s before next session")
		await asyncio.sleep(rest_time)

		i += batch_size

	logger.info("🎉 Done crawling all keywords")


async def schedule(config: dict, bot_name: str):

	sleep    = config.get("sleep", 5)
	bot_type = config.get("bot_type", "")
	logger.info(f"[{bot_name}] Sleep config in database: {sleep} minutes")

	INTERVAL = sleep * 60
	while True:
		try:
			sleep_manager = SleepManager(logger)
			if sleep_manager.is_sleep_time():
				await sleep_manager.sleep_until_wakeup()
				continue

			logger.info(f"[{bot_name}] Crawl with {bot_type}")

			if settings.DEBUG:
				await run_test(bot_type, bot_name)
			else:
				await run_with_gpm(bot_type, bot_name)

			logger.info(f"[{bot_name}] === Run completed. Sleeping for {sleep} minutes ===")
		except Exception as e:
			logger.exception(f"[{bot_name}] Unhandled exception in run(): {e}")

		await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
	bot_name = settings.BOT_NAME
	config   = db.tiktok_bot_configs.find_one({"bot_name": bot_name})
	if not config:
		raise ValueError("Bot config not found")

	async def main():
		await asyncio.gather(
			schedule(config, bot_name),
			heartbeat_loop(config)
		)

	asyncio.run(main())
