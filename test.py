import asyncio
import random
import time

from playwright.async_api import async_playwright

from src.api import postToESUnclassified
from src.parsers.video_parser import TiktokPost


SEARCH_API = "/api/search/general/full/"
KEYWORDS = ["python"]

async def human_delay(min_ms=800, max_ms=1500):
	await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

async def crawl_search(keyword: str):
	async with async_playwright() as p:
		print("🚀 Launch browser")
		chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"  # đường dẫn Chrome trên Windows

		browser = await p.chromium.launch(
			headless=False,
			executable_path=chrome_path,
			args=["--disable-blink-features=AutomationControlled"]
		)

		context = await browser.new_context(storage_state="tiktok_profile.json")
		
		page = await context.new_page()

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

		print("🚀 Open TikTok")
		await page.goto("https://www.tiktok.com", timeout=60000)

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

		# await browser.close()
		return items





async def main():
	data = await crawl_search("Hà nội")
	print(f"✅ Got {len(data)} items")

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

if __name__ == "__main__":
	asyncio.run(main())