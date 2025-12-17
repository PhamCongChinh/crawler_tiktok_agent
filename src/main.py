import asyncio
import random
from playwright.async_api import async_playwright
import time
import urllib.parse
import json

from crawler_keywords import CrawlerKeyword
from crawler_urls import CrawlerUrl
from parsers.video_parser import TiktokPost
from api import postToESUnclassified
from config.settings import settings
from utils import delay

from config.logging import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)

async def extract_video_info(page):
    raw = await page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
    data = json.loads(raw)
    root = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(root, f, ensure_ascii=False, indent=4)

    return {
        "pub_time": int(root["createTime"]),
        "description": root["desc"],
        "video_id": root["id"],
        "unique_id": root["author"]["uniqueId"],
        "comments": root["stats"]["commentCount"],
        "shares": root["stats"]["shareCount"],
        "reactions": root["stats"]["diggCount"],
        "favors": root["stats"]["collectCount"],
        "views": root["stats"]["playCount"],
        "auth_id": root["author"]["id"],
        "auth_name": root["author"]["nickname"],
    }


async def scroll_tiktok(page, times=1):
    for _ in range(times):
        distance = random.randint(1500, 3500)
        await page.mouse.wheel(0, distance)
        await page.wait_for_timeout(random.randint(900, 1800))


async def run():
    async with async_playwright() as p:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"  # đường dẫn Chrome trên Windows

        browser = await p.chromium.launch(
            headless=False,
            executable_path=chrome_path,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(storage_state="tiktok_profile.json")

        await context.route("**/*", lambda route, request: (
            route.abort() 
            if request.resource_type in ["image", "media", "font", "stylesheet"] 
            else route.continue_()
        ))

        page = await context.new_page()
        await delay(800, 1500)

        await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=60000)
        logger.info("Đã vào trang chủ TikTok")

        with open("keywords.json", "r", encoding="utf8") as f:
            keywords = json.load(f)


        await CrawlerKeyword.crawler_keyword(context=context, page=page, keywords=keywords)


        # with open("urls.json", "r", encoding="utf8") as f:
        #     urls = json.load(f)

        # crawler_urls = await CrawlerUrl.crawler_url(context=context, page=page, urls=urls)
        
        # for keyword in keywords:
        #     try:
        #         unix_time = int(time.time())
        #         encoded = urllib.parse.quote(keyword)
        #         url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

        #         await page.goto(url, wait_until="networkidle", timeout=60000)
        #         await delay(1500, 3000)

        #         try:
        #             error_box = page.locator("h2[data-e2e='search-error-title']")

        #             if await error_box.is_visible():
        #                 logger.info(f"[{keyword}] Error hiển thị: Something went wrong")
        #                 btn = page.locator("button:has-text('Try again')")
        #                 if await btn.is_visible():
        #                     logger.info(f"[{keyword}] Try again visible → click")
        #                     await btn.click()
        #                     await asyncio.sleep(2)
        #         except Exception as e:
        #             logger.error(f"[{keyword}] Lỗi khi xử lý error box: {e}")
                
        #         await scroll_tiktok(page=page, times=1)

        #         await page.wait_for_selector("#search_top-item-list", timeout=60000)
       
        #         locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
        #         count = await locator.count()
        #         logger.info(f"[{keyword}] Tìm được {count} item")

        #         data = []
        #         limit = min(5, count)
            
        #         for i in range(limit):
        #             new_page = None
        #             try:
        #                 item = locator.nth(i)
        #                 video_url = await item.locator("a[href*='/video/']").get_attribute("href")
        #                 logger.info(f"[{keyword}][{i+1}] Link video: {video_url}")

        #                 await delay(1200, 2500)
        #                 new_page = await context.new_page()
        #                 await new_page.goto(video_url)
        #                 await new_page.wait_for_load_state("domcontentloaded")
                    
        #                 await delay(20000, 30000)

        #                 video_info = await extract_video_info(new_page)
                        
        #                 item = TiktokPost().new(video_info)
        #                 data.append(item)
        #             except Exception as e:
        #                 logger.error(f"[{keyword}] Lỗi khi crawl video item {i}: {e}")
        #             finally:
        #                 await delay(1000, 2000)
        #                 try:
        #                     await new_page.close()
        #                 except:
        #                     pass

        #         await delay(4000, 7000)
        #         try:
        #             result = await postToESUnclassified(data)
        #             if not result["success"]:
        #                 logger.error(f'[{keyword}] Lỗi khi đẩy dữ liệu: { result["error"]}')
        #             else:
        #                 logger.info(f'✅ Thành công: gửi {result["total"]} bài viết')
        #         except Exception as e:
        #                 logger.error(f"Lỗi khi gửi dữ liệu lên ES: {e}")

        #         await delay(2500, 4000)

        #     except Exception as e:
        #         logger.error(f"🔥 Lỗi vòng keyword '{keyword}': {e}")
        #         continue
            
async def schedule():
    while True:
        try:
            logger.info("---------------Bắt đầu chạy run() -----------------")
            await run()
            logger.info(f"=== Hoàn thành, chờ {settings.SLEEP} phút ===")
        except Exception as e:
            logger.error(f"Lỗi trong run(): {e}")

        await asyncio.sleep(settings.SLEEP * 60)
if __name__ == "__main__":
    asyncio.run(schedule())