import asyncio
from playwright.async_api import async_playwright
import time
import urllib.parse
import json

from parsers.video_parser import TiktokPost
from api import postToESUnclassified
from utils import delay

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

        keywords = ["Tập Đoàn T&T"]

        for keyword in keywords:
            unix_time = int(time.time())
            encoded = urllib.parse.quote(keyword)
            url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            await delay(2000, 5000)

            error_box = page.locator("h2[data-e2e='search-error-title']")

            if await error_box.is_visible():
                print("Error hiển thị: Something went wrong")
                btn = page.locator("button:has-text('Try again')")
                if await btn.is_visible():
                    print("Try again visible → click")
                    await btn.click()
                    await asyncio.sleep(2)


            await page.wait_for_selector("#search_top-item-list", timeout=60000)
       
            locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
            count = await locator.count()

            data = []
            
            for i in range(5):
                print("Item:", i)
                item = locator.nth(i)
                video_url = await item.locator("a[href*='/video/']").get_attribute("href")
                print("Link video:", video_url)

                await delay(1000, 3000)
                new_page = await context.new_page()
                await new_page.goto(video_url)
                await new_page.wait_for_load_state("domcontentloaded")
            
                await delay(2000, 5000)

                video_info = await extract_video_info(new_page)
                item = TiktokPost().new(video_info)
                data.append(item)

                await delay(2000, 5000)
                await new_page.close()

            # Send kafka
            # with open("data.json", "w", encoding="utf-8") as f:
            #     json.dump(data, f, ensure_ascii=False, indent=4)
            await delay(2000, 5000)
            result = await postToESUnclassified(data)
            print(result)

async def schedule():
    while True:
        try:
            print("=== Bắt đầu chạy run() ===")
            await run()
            print("=== Hoàn thành, ngủ 15 phút ===")
        except Exception as e:
            print("Lỗi trong run():", e)

        await asyncio.sleep(5 * 60)   # 15 phút
if __name__ == "__main__":
    asyncio.run(schedule())

