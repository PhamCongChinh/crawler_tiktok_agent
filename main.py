import asyncio
import random
import logging
import requests

from playwright.async_api import async_playwright

from src.scrapers.search import crawl_tiktok_search
from src.db.mongo import MongoDB
from src.config.logging import setup_logging
from src.utils.delay_utils import delay
from src.utils.sleep_manager import SleepManager
from src.config.settings import settings


setup_logging()
logger = logging.getLogger(__name__)

db         = MongoDB.get_db()
bot_config = db.tiktok_bot_configs


async def run_with_gpm(bot_type: str, bot_name: str):
	config = bot_config.find_one({"bot_name": bot_name})
	if not config:
		raise ValueError(f"Bot config not found for {bot_name}")

	GPM_API    = config["gpm_api"]
	PROFILE_ID = config["profile_id"]
	org_ids    = [int(x) for x in config.get("org_id", [])]

	resp = requests.get(f"{GPM_API}/profiles/start/{PROFILE_ID}")
	resp.raise_for_status()
	debug_addr = resp.json()["data"]["remote_debugging_address"]

	browser = None
	try:
		async with async_playwright() as p:
			browser = await p.chromium.connect_over_cdp(f"http://{debug_addr}")
			if not browser.contexts:
				raise Exception("No browser context found from GPM")

			context  = browser.contexts[0]
			docs     = list(db.keyword.find({"org_id": {"$in": org_ids}}))
			keywords = [d["keyword"] for d in docs]

			logger.info(f"[{bot_name}] Total keywords: {len(keywords)}")
			await delay(1000, 2000)
			await crawl_tiktok_search(context, keywords, bot_name)

	except Exception as e:
		logger.exception(f"[{bot_name}] Error in run_with_gpm(): {e}")
	finally:
		try:
			if browser:
				await browser.close()
		except Exception:
			pass
		try:
			requests.get(f"{GPM_API}/profiles/close/{PROFILE_ID}")
			logger.info(f"[{bot_name}] GPM profile stopped")
		except Exception as e:
			logger.error(f"[{bot_name}] Failed to stop GPM profile: {e}")


async def schedule(config: dict, bot_name: str):
	sleep    = config.get("sleep", 5)
	bot_type = config.get("bot_type", "")
	INTERVAL = sleep * 60
	logger.info(f"[{bot_name}] Interval: {sleep} minutes")

	while True:
		try:
			sleep_manager = SleepManager(logger)
			if sleep_manager.is_sleep_time():
				await sleep_manager.sleep_until_wakeup()
				continue

			logger.info(f"[{bot_name}] Starting crawl ({bot_type})")
			await run_with_gpm(bot_type, bot_name)

			logger.info(f"[{bot_name}] Run completed. Sleeping {sleep} minutes...")
		except Exception as e:
			logger.exception(f"[{bot_name}] Unhandled exception: {e}")

		await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
	bot_name = settings.BOT_NAME
	config   = db.tiktok_bot_configs.find_one({"bot_name": bot_name})
	print(config)
	if not config:
		raise ValueError("Bot config not found")

	asyncio.run(schedule(config, bot_name))
