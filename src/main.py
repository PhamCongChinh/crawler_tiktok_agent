import asyncio
from typing import Optional
from playwright.async_api import async_playwright
import time
import urllib.parse
import json
from datetime import datetime

from parsers.video_parser import TiktokPost
from api import postToESUnclassified

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

async def run():
    async with async_playwright() as p:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"  # đường dẫn Chrome trên Windows

        browser = await p.chromium.launch(
            headless=False,
            executable_path=chrome_path,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(storage_state="tiktok_profile.json")
        page = await context.new_page()
        await page.wait_for_timeout(3000)

        keywords = [
            "Đỗ Mỹ Linh",
            "Bầu Hiển",
            "Tập đoàn T&T",
            "Chủ tịch Hà Nội FC",
            "CLB Hà Nội","T&T"
        ]

        for keyword in keywords:
            unix_time = int(time.time())
            encoded = urllib.parse.quote(keyword)
            url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

            # Mở Google
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            await page.wait_for_selector("#search_top-item-list")
       
            locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
            count = await locator.count()

            data = []
            
            for i in range(5):
                print("Item:", i)
                item = locator.nth(i)
                video_url = await item.locator("a[href*='/video/']").get_attribute("href")
                print("Link video:", video_url)

                new_page = await context.new_page()
                await new_page.goto(video_url)
                await new_page.wait_for_load_state("domcontentloaded")
            
                await new_page.wait_for_timeout(3000)

                video_info = await extract_video_info(new_page)
                item = TiktokPost().new(video_info)
                data.append(item)

                await new_page.wait_for_timeout(3000)
                await new_page.close()

            # Send kafka
            # with open("data.json", "w", encoding="utf-8") as f:
            #     json.dump(data, f, ensure_ascii=False, indent=4)
            result = await postToESUnclassified(data)
            print(result)





        # keyword = 'Đỗ Mỹ Linh'

        # unix_time = int(time.time())
        # encoded = urllib.parse.quote(keyword)

        # # Mở Google
        # await page.goto(
        #     f"https://www.tiktok.com/search?q={encoded}&t={unix_time}",
        #     wait_until="domcontentloaded",
        #     timeout=60000
        # )

        # await page.wait_for_selector("#search_top-item-list")
       
        # locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
        # count = await locator.count()

        # data = []
        
        # for i in range(5):
        #     print("Item:", i)
        #     item = locator.nth(i)
        #     video_url = await item.locator("a[href*='/video/']").get_attribute("href")
        #     print("Link video:", video_url)

        #     new_page = await context.new_page()
        #     await new_page.goto(video_url)
        #     await new_page.wait_for_load_state("domcontentloaded")
        
        #     await new_page.wait_for_timeout(3000)

        #     video_info = await extract_video_info(new_page)
        #     item = TiktokPost().new(video_info)
        #     data.append(item)

        #     await new_page.wait_for_timeout(3000)
        #     await new_page.close()

        # # Send kafka
        # # with open("data.json", "w", encoding="utf-8") as f:
        # #     json.dump(data, f, ensure_ascii=False, indent=4)
        # result = await postToESUnclassified(data)
        # print(result)

async def schedule():
    while True:
        try:
            print("=== Bắt đầu chạy run() ===")
            await run()
            print("=== Hoàn thành, ngủ 15 phút ===")
        except Exception as e:
            print("Lỗi trong run():", e)

        await asyncio.sleep(30 * 60)   # 15 phút
if __name__ == "__main__":
    asyncio.run(schedule())

