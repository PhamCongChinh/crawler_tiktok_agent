import asyncio
import random
import time
import urllib
import logging
from collections import defaultdict

from src.api import postToESUnclassified
from src.parsers.video_parser import TiktokPost
from src.utils.scroll_utils import human_scroll
from src.utils.browser_actions import random_view_video

logger = logging.getLogger(__name__)

TIKTOK_URL  = "https://www.tiktok.com"
API_FILTERS = ["/api/search/item/full/"]
GOTO_TIMEOUT = 60_000
MAX_RETRIES  = 3

BATCH_MIN = 5
BATCH_MAX = 10


async def _goto_with_retry(page, url: str, bot_name: str, label: str) -> bool:
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


async def crawl_tiktok_search(context, keywords: list[str], bot_name: str) -> None:
	videos_by_keyword   = defaultdict(list)
	seen_ids_by_keyword = defaultdict(set)

	i     = 0
	total = len(keywords)

	while i < total:
		batch_keywords = keywords[i : i + random.randint(BATCH_MIN, BATCH_MAX)]
		logger.info(f"[{bot_name}] 🚀 New session with {len(batch_keywords)} keywords")

		page            = await context.new_page()
		current_keyword = None
		days_ago        = int(time.time()) - 7 * 24 * 60 * 60

		async def on_response(res):
			nonlocal current_keyword
			if not current_keyword or not any(api in res.url for api in API_FILTERS):
				return
			try:
				body = await res.json()
			except Exception:
				return
			if not body or body.get("status_code") != 0:
				return
			for item in body.get("item_list", []):
				vid = item.get("id")
				if vid and vid not in seen_ids_by_keyword[current_keyword]:
					seen_ids_by_keyword[current_keyword].add(vid)
					videos_by_keyword[current_keyword].append(item)

		page.on("response", on_response)

		if not await _goto_with_retry(page, TIKTOK_URL, bot_name, "homepage"):
			await page.close()
			i += len(batch_keywords)
			await asyncio.sleep(random.randint(30, 60))
			continue

		await page.wait_for_timeout(random.randint(4000, 7000))
		await page.mouse.move(
			random.randint(100, 900),
			random.randint(100, 600),
			steps=random.randint(10, 30),
		)
		await page.wait_for_timeout(random.randint(500, 1500))

		for keyword in batch_keywords:
			logger.info(f"[{bot_name}] [{keyword}] Searching...")

			current_keyword              = keyword
			videos_by_keyword[keyword]   = []
			seen_ids_by_keyword[keyword] = set()

			search_url = f"{TIKTOK_URL}/search/video?q={urllib.parse.quote(keyword)}&t={int(time.time() * 1000)}"

			if not await _goto_with_retry(page, search_url, bot_name, keyword):
				current_keyword = None
				continue

			await page.wait_for_timeout(random.randint(3000, 5000))

			locator = page.locator("[id^='grid-item-container-']")
			await human_scroll(page, locator, times=random.randint(1, 4))
			await random_view_video(page, watch_time_range=(5000, 12000))

			videos = videos_by_keyword[keyword]
			logger.info(f"[{bot_name}] [{keyword}] Collected {len(videos)} videos")

			results = []
			for item in videos:
				try:
					pub_time = int(item.get("createTime", 0))
					if pub_time < days_ago:
						continue
					author = item.get("author", {})
					stats  = item.get("stats", {})
					results.append(TiktokPost().new({
						"keyword":     keyword,
						"video_id":    item.get("id"),
						"description": item.get("desc"),
						"pub_time":    pub_time,
						"unique_id":   author.get("uniqueId", ""),
						"auth_id":     author.get("id", 0),
						"auth_name":   author.get("nickname", ""),
						"comments":    stats.get("commentCount", 0),
						"shares":      stats.get("shareCount", 0),
						"reactions":   stats.get("diggCount", 0),
						"favors":      stats.get("collectCount", 0),
						"views":       stats.get("playCount", 0),
					}))
				except Exception as e:
					logger.error(f"[{bot_name}] [{keyword}] Parse error: {e}")

			if results:
				try:
					result = await postToESUnclassified(results)
					logger.info(f"[{bot_name}] [{keyword}] Posted {len(results)} posts → {result.get('status')}")
				except Exception as e:
					logger.error(f"[{bot_name}] [{keyword}] Post error: {e}")

			current_keyword = None
			wait = random.randint(60, 90)
			logger.info(f"[{bot_name}] Waiting {wait}s before next keyword...")
			await asyncio.sleep(wait)

		logger.info(f"[{bot_name}] 🛑 Closing page")
		await page.close()

		rest = random.randint(180, 300)
		logger.info(f"[{bot_name}] 😴 Resting {rest}s before next session")
		await asyncio.sleep(rest)

		i += len(batch_keywords)

	logger.info(f"[{bot_name}] 🎉 Done crawling all keywords")
