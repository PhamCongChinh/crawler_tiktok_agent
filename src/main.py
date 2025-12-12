import asyncio
from playwright.async_api import async_playwright
import time
import urllib.parse
import json

from parsers.video_parser import TiktokPost
from api import postToESUnclassified
from utils import delay


from logging_config import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)



async def extract_video_info(page):
    raw = await page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
    data = json.loads(raw)
    root = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
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


async def scroll_tiktok(page):
    for _ in range(5):  # scroll 50 lần
        await page.evaluate("window.scrollBy(0, 2500);")
        await page.wait_for_timeout(4200)

async def handle_something_went_wrong(page):
    # Check error text
    error = page.locator("h2[data-e2e='search-error-title']:has-text('Something went wrong')")

    if await error.count() > 0:
        print("Detected 'Something went wrong' → trying to recover")

        # Try click Try Again
        btn = page.locator("button:has-text('Try again')")
        if await btn.count() > 0:
            await btn.click()
            await asyncio.sleep(3)
            return True
        
        # If no button, reload page
        print("Try again button not found → reload page")
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        return True

    return False

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
        await delay(2000, 4000)

        with open("keywords.json", "r", encoding="utf8") as f:
            keywords = json.load(f)

        logger.info(keywords)

        for keyword in keywords:
            try:
                unix_time = int(time.time())
                encoded = urllib.parse.quote(keyword)
                url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await delay(2000, 5000)

                try:
                    error_box = page.locator("h2[data-e2e='search-error-title']")

                    if await error_box.is_visible():
                        logger.info("Error hiển thị: Something went wrong")
                        btn = page.locator("button:has-text('Try again')")
                        if await btn.is_visible():
                            logger.info("Try again visible → click")
                            await btn.click()
                            await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý error box: {e}")


                await page.wait_for_selector("#search_top-item-list", timeout=60000)
       
                locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
                count = await locator.count()

                data = []
            
                for i in range(count):
                    try:
                        logger.info(f"Item: {i}")
                        item = locator.nth(i)
                        video_url = await item.locator("a[href*='/video/']").get_attribute("href")
                        logger.info(f"Link video: {video_url}")

                        await delay(1000, 3000)
                        new_page = await context.new_page()
                        await new_page.goto(video_url)
                        await new_page.wait_for_load_state("domcontentloaded")
                    
                        await delay(2000, 5000)

                        video_info = await extract_video_info(new_page)
                        item = TiktokPost().new(video_info)
                        data.append(item)
                    except Exception as e:
                        logger.error(f"Lỗi khi crawl video item {i}: {e}")
                    finally:
                        await delay(2000, 5000)
                        try:
                            await new_page.close()
                        except:
                            pass

                await delay(2000, 5000)
                try:
                    result = await postToESUnclassified(data)
                    if not result["success"]:
                        print("❌ Lỗi khi đẩy dữ liệu:", result["error"])
                    else:
                        print("✅ Thành công:", result["total"])
                except Exception as e:
                        logger.error(f"Lỗi khi gửi dữ liệu lên ES: {e}")

                await delay(2000, 5000)

            except Exception as e:
                logger.error(f"🔥 Lỗi vòng keyword '{keyword}': {e}")
                # vẫn tiếp tục keyword tiếp theo
                continue
            
async def schedule():
    while True:
        try:
            logger.info("=== Bắt đầu chạy run() ===")
            await run()
            logger.info("=== Hoàn thành, ngủ 15 phút ===")
        except Exception as e:
            logger.error(f"Lỗi trong run(): {e}")

        await asyncio.sleep(30 * 60)   # 15 phút
if __name__ == "__main__":
    asyncio.run(schedule())

