import asyncio
import json
from api import postToESUnclassified
from config.logging import setup_logging
import logging

from parsers.video_parser import TiktokPost
from utils import delay
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


class CrawlerUrl:

    async def crawler_url(context, page, urls):
        logger.info(f"Loaded {len(urls)} urls: {urls}")
        await delay(2000, 4000)

        for url in urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await page.wait_for_selector("#user-post-item-list", timeout=60000)
                locator = page.locator("#user-post-item-list [id^='grid-item-container-']")
                count = await locator.count()
                
                data = []
                
                for i in range(min(5,count)):
                    try:

                        if i >= 3 and (i - 3) % 4 == 0:
                            await page.evaluate("window.scrollBy(0, 500)")
                            await asyncio.sleep(1)

                        item = locator.nth(i)
                        video_url = await item.locator("a[href*='/video/']").get_attribute("href")
                        logger.info(f"[{i}]Link video: {video_url}")

                        await delay(2000, 4000)
                        new_page = await context.new_page()
                        await new_page.goto(video_url)
                        await new_page.wait_for_load_state("domcontentloaded")
                    
                        await delay(20000, 30000)

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
            except:
                pass