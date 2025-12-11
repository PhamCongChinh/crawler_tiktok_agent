import asyncio
from typing import Optional
from playwright.async_api import async_playwright
import time
import urllib.parse
import json
from datetime import datetime

from parsers.video_parser import TiktokPost






async def extract_video_info(page):
    # data = {}

    # data["url"] = page.url

    # # Description
    # desc_locator = page.locator('div[data-e2e="browse-video-desc"]')
    # text = await desc_locator.inner_text()
    # data["content"] = text


    # # --- LIKE / COMMENT / SHARE ---
    # def safe_int(x):
    #     if not x:
    #         return 0
    #     x = x.lower().replace("k", "000").replace("m", "000000")
    #     return int("".join([c for c in x if c.isdigit()]))
    # try:
    #     likes = await page.locator('[data-e2e="browse-like-count"]').inner_text()
    #     comments = await page.locator('[data-e2e="browse-comment-count"]').inner_text()
    #     # shares = await page.locator('[data-e2e="share-count"]').inner_text()

    #     data["likes"] = safe_int(likes)
    #     data["comments"] = safe_int(comments)
    #     # data["shares"] = safe_int(shares)
    # except:
    #     data["likes"] = data["comments"] = 0

    

    raw = await page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
    data = json.loads(raw)

    # đi vào structure
    root = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]

    publish_timestamp = int(root["createTime"])
    publish_datetime = datetime.fromtimestamp(publish_timestamp)

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

        
        # "hashtags": [x["hashtagName"] for x in root.get("textExtra", []) if x.get("hashtagName")],
        # "author_username": root["author"]["uniqueId"],
        # "author_nickname": root["author"]["nickname"],

        # "subject_id": root["author"]["nickname"],
        # # stats
        # "likes": root["stats"]["diggCount"],
        # "comments": root["stats"]["commentCount"],
        # "shares": root["stats"]["shareCount"],
        # "views": root["stats"]["playCount"],

        # # video URL (watermarked)
        # "download_addr": root["video"]["downloadAddr"],
        # # video URL (no watermark)
        # "play_addr": root["video"]["playAddr"],
    }

    return root


async def scroll_tiktok(page):
    for _ in range(5):  # scroll 50 lần
        await page.evaluate("window.scrollBy(0, 2500);")
        await page.wait_for_timeout(4200)

async def run():
    async with async_playwright() as p:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"  # đường dẫn Chrome trên Windows

        # Khởi tạo trình duyệt Chromium
        browser = await p.chromium.launch(
            headless=False,
            executable_path=chrome_path,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(storage_state="tiktok_profile.json")
        page = await context.new_page()
        await page.wait_for_timeout(3000)
        keyword = 'Đỗ Mỹ Linh'
        unix_time = int(time.time())
        print(unix_time)

        encoded = urllib.parse.quote(keyword)
        print(encoded)

        # Mở Google
        await page.goto(
            f"https://www.tiktok.com/search?q={encoded}&t={unix_time}",
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Chờ danh sách xuất hiện
        await page.wait_for_selector("#search_top-item-list")
       
        # await page.wait_for_selector("#search_top-item-list")
        # items = await page.query_selector_all("#search_top-item-list [id^='grid-item-container-']")
        # print("Tìm thấy:", len(items))
        locator = page.locator("#search_top-item-list [id^='grid-item-container-']")
        count = await locator.count()

        data = []
        
        for i in range(3):
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

            await new_page.close()
            # await page.wait_for_timeout(5000)
            # await page.go_back()
            # await page.wait_for_load_state("domcontentloaded")
            await new_page.wait_for_timeout(3000)
            # items = await page.locator("#search_top-item-list .grid-item-container").all()



        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # first = items[0]   # video đầu tiên

        # await page.wait_for_timeout(3000)
        # # Click mở video
        # await first.click(force=True)

        # # Chờ trang video load xong
        # await page.wait_for_load_state("domcontentloaded")
        # print("Đã mở video:", page.url)


        # await page.wait_for_timeout(3000)
        # await page.reload()

        # await page.evaluate("""
        #     const vid = document.querySelector('video');
        #     if (vid) { vid.muted = false; vid.play(); }
        # """)
        # await page.wait_for_timeout(5000)

        # # Click nút Next video
        # # await page.click('button[data-e2e="arrow-right"]', force=True)

        # # print("Đã click next video:", page.url)

        # # for i in range(5):
        # #     print(f"Click lần {i+1}")
        # #     await page.click('button[data-e2e="arrow-right"]')
        # #     await asyncio.sleep(5)  # đợi video chuyển

        # # desc_locator = page.locator('div[data-e2e="browse-video-desc"]')
        # # text = await desc_locator.inner_text()
        # # print(text)

        
        # video_info = await extract_video_info(page)

        # data = []
        # item = TiktokPost().new(video_info)
        # with open("item.json", "w", encoding="utf-8") as f:
        #     json.dump(item, f, ensure_ascii=False, indent=4)

        # data.append(item)

        # await page.wait_for_timeout(5000)


        # with open("item.json", "w", encoding="utf-8") as f:
        #     json.dump(item, f, ensure_ascii=False, indent=4)
        # await page.wait_for_timeout(10000000)
        # await browser.close()

asyncio.run(run())

