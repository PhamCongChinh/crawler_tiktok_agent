import asyncio
import json
import time

import urllib
from api import postToESUnclassified
from config.logging import setup_logging
import logging

from parsers.video_parser import TiktokPost
from utils import delay, detect_captcha, extract_video_info, smart_delay
setup_logging()
logger = logging.getLogger(__name__)

# async def extract_video_info(page):
#     raw = await page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
#     data = json.loads(raw)
#     root = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]

#     return {
#         "pub_time": int(root["createTime"]),
#         "description": root["desc"],
#         "video_id": root["id"],
#         "unique_id": root["author"]["uniqueId"],
#         "comments": root["stats"]["commentCount"],
#         "shares": root["stats"]["shareCount"],
#         "reactions": root["stats"]["diggCount"],
#         "favors": root["stats"]["collectCount"],
#         "views": root["stats"]["playCount"],
#         "auth_id": root["author"]["id"],
#         "auth_name": root["author"]["nickname"],
#     }


class CrawlerKeyword:

    async def crawler_keyword(context, page, keywords):
        logger.info(f"Loaded {len(keywords)} urls: {keywords}")
        await delay(2000, 4000)

        for keyword in keywords:
            try:
                unix_time = int(time.time())
                encoded = urllib.parse.quote(keyword)
                url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

                await page.goto(
                    url,
                    wait_until="networkidle",
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
                logger.info(f"Có tất cả {count} tin bài")

                data = []
            
                for i in range(count):
                    try:
                        item = locator.nth(i)

                        time_text = (await item.inner_text()).lower()
                        if "ago" not in time_text and "trước" not in time_text:
                            continue
                        

                        # 2️⃣ Scroll CHỈ khi item hợp lệ
                        if i >= 3 and (i - 3) % 4 == 0:
                            await page.evaluate("window.scrollBy(0, 500)")
                            await delay(800, 1200)
                            if await detect_captcha(page):
                                logger.warning("⚠️ CAPTCHA detected (list page) – chờ 60s")
                                await delay(90000, 120000)
                                continue

                        video_url = await item.locator("a[href*='/video/']").get_attribute("href")
                        if not video_url:
                            continue

                        logger.info(f"[{i+1}] {video_url}")

                        await delay(*smart_delay())

                        new_page = await context.new_page()
                        await new_page.goto(video_url, wait_until="domcontentloaded")
                        # await new_page.wait_for_load_state("domcontentloaded")

                        if await detect_captcha(new_page):
                            logger.warning("⚠️ CAPTCHA detected – chờ 60s")
                            await delay(90000, 120000)
                            await new_page.close()
                            continue
                    
                        await delay(20000, 30000)

                        video_info = await extract_video_info(new_page)
                        data.append(TiktokPost().new(video_info))

                    except Exception as e:
                        logger.error(f"Lỗi khi crawl video item {i}: {e}")
                    finally:
                        try:
                            await new_page.close()
                        except:
                            pass

                if data:
                    try:
                        result = await postToESUnclassified(data)
                        if not result["success"]:
                            logger.error(f"❌ Lỗi ES: {result['error']}")
                        else:
                            logger.info(f"✅ Đẩy ES thành công: {result['total']}")
                    except Exception as e:
                            logger.error(f"Lỗi khi gửi dữ liệu lên ES: {e}")

                await delay(2000, 4000)

            except Exception as e:
                logger.error(f"🔥 Lỗi vòng keyword '{keyword}': {e}")
                continue