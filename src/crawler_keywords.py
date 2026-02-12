import asyncio
from datetime import datetime
import json
import time
import random
import hashlib

import urllib
from src.config.redis_client import redis_client
from src.api import postToESUnclassified
from src.config.logging import setup_logging
import logging

from src.parsers.video_parser import TiktokPost
from src.utils import delay, extract_video_info
setup_logging()
logger = logging.getLogger(__name__)

from collections import defaultdict
API_FILTERS = [
    "/api/search",
    "/api/post",
    "/api/item_list",
    "/api/recommend"
]

class CrawlerKeyword:

    @staticmethod
    async def crawler_keyword(context, page, keywords):
        logger.info(f"Đã tải {len(keywords)} từ khóa")
        await delay(2000, 4000)

        for idx, keyword in enumerate(keywords, start=1):
            logger.info(f"🔍 Bắt đầu crawl keyword {idx}/{len(keywords)}: {keyword}")

            try:
                await CrawlerKeyword._crawl_single_keyword(
                    context=context,
                    page=page,
                    keyword=keyword
                )

                # Nghỉ giữa các từ khóa
                await asyncio.sleep(5000000000000)

                if idx % 10 == 0:
                    time_sleep = random.randint(180, 300)
                    logger.warning(f"Đã crawl 10 keyword, nghỉ {time_sleep} giây")
                    await asyncio.sleep(time_sleep)

            except Exception as e:
                logger.exception(f"[{keyword}] 🔥 Lỗi keyword")
                continue

            await delay(20000, 40000)

    # =======================

    @staticmethod
    async def _crawl_single_keyword(context, page, keyword: str):
        await delay(2000, 5000)
        unix_time = int(time.time() * 1000)
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await delay(2000, 5000)

        # a = await CrawlerKeyword.capture_xhr(page)
        # print(a)

        await page.get_by_role("button", name="Video").click()

        xhr_calls = defaultdict(dict)

        async def on_request(req):
            if any(api in req.url for api in API_FILTERS):
                xhr_calls[req.url]["request"] = {
                    "method": req.method,
                    "headers": req.headers,
                    "payload": req.post_data,
                    "timestamp": datetime.utcnow().isoformat()
                }

        async def on_response(res):
            if any(api in res.url for api in API_FILTERS):
                try:
                    body = await res.json()
                except:
                    body = None

                xhr_calls[res.url]["response"] = {
                    "status": res.status,
                    "headers": res.headers,
                    "body": body,
                    "timestamp": datetime.utcnow().isoformat()
                }

        page.on("request", on_request)
        page.on("response", on_response)

        with open("xhr_calls123.json", "w", encoding="utf-8") as f:
            json.dump(xhr_calls, f, ensure_ascii=False, indent=2)

        print(f"✅ Done. Captured {len(xhr_calls)} API calls")

        # _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]



        # await page.get_by_role("button", name="Video").click()
        # # await page.locator('span', has_text='Video').click()

        # await delay(2000, 5000)

        # locator = page.locator("[id^='grid-item-container-']")


        # # Scroll 5 lần để load video
        # await CrawlerKeyword.human_scroll(page, locator, times=5)

        # count = await locator.count()
        # logger.info(f"[{keyword}] Tổng video sau scroll: {count}")

        # results = []

        # for i in range(count):
        #     item = locator.nth(i)

        #     try:
        #         if not await CrawlerKeyword._is_recent_item(item):
        #             continue

        #         await item.scroll_into_view_if_needed()
        #         await delay(300, 600)

        #         video_url = await CrawlerKeyword._get_video_url(item)
        #         if not video_url:
        #             continue

        #         logger.info(f"[{keyword}] [{i+1}/{count}] {video_url}")

        #         # Nếu đã tồn tại trong Redis thì bỏ qua
        #         if not await CrawlerKeyword.should_crawl_video(redis_client, video_url):
        #             logger.info(f"[{keyword}] SKIP (cached): {video_url}")
        #             continue

        #         post = await CrawlerKeyword._crawl_video(context, video_url)
        #         if post:
        #             results.append(post)

        #         await delay(4000,8000)

        #     except Exception as e:
        #         logger.error(f"[{keyword}] ❌ Lỗi item {i}: {e}")

        # # await CrawlerKeyword._push_to_es(keyword, results)
        # if results:
        #     await CrawlerKeyword._push_to_es(keyword, results)
        #     logger.info(f"[{keyword}] ✅ Đã push {len(results)} video vào ES")
        # else:
        #     logger.warning(f"[{keyword}] ⚠️ Không có video hợp lệ để push")

    # =======================

    @staticmethod
    async def capture_xhr(page):
        async def on_response(response):
            if "api/search" in response.url:
                try:
                    data = await response.json()
                    print(data)
                except:
                    pass

        page.on("response", on_response)

    @staticmethod
    def video_key(video_url: str) -> str:
        h = hashlib.md5(video_url.encode()).hexdigest()
        return f"tiktok:video:{h}"

    @staticmethod
    async def should_crawl_video(redis_client, video_url: str, ttl=86400) -> bool:
        key = CrawlerKeyword.video_key(video_url)

        # SET key value NX EX ttl
        # return True nếu SET thành công (chưa tồn tại)
        ok = await redis_client.set(key, 1, nx=True, ex=ttl)
        return ok is True

    @staticmethod
    async def human_scroll(page, locator, times: int = 1):
        """
        Scroll giống hành vi người dùng thật
        :param page: playwright page
        :param locator: locator video items
        :param times: số lần scroll
        """
        for i in range(times):
            count = await locator.count()
            if count == 0:
                break

            # Move mouse nhẹ (giống người)
            await page.mouse.move(
                random.randint(200, 600),
                random.randint(200, 500)
            )

            # Scroll tới item cuối
            await locator.nth(count - 1).scroll_into_view_if_needed()

            # dừng xem ngắn
            await page.wait_for_timeout(random.randint(800, 1500))

            # 🔄 20% scroll ngược lại
            if random.random() < 0.2:
                await page.mouse.wheel(0, -random.randint(150, 300))
                await page.wait_for_timeout(random.randint(200, 400))

            # 😵‍💫 10% đứng im rất lâu (lướt mà quên scroll)
            if random.random() < 0.1:
                long_pause = random.randint(6000, 12000)
                await page.wait_for_timeout(long_pause)

            # Người dùng thường dừng xem
            await page.wait_for_timeout(random.randint(700, 1200))

    # @staticmethod
    # async def _handle_search_error(page, keyword):
    #     try:
    #         error_box = page.locator("h2[data-e2e='search-error-title']")
    #         if await error_box.is_visible():
    #             logger.warning(f"[{keyword}] ⚠️ Search error")
    #             btn = page.locator("button:has-text('Try again')")
    #             if await btn.is_visible():
    #                 await btn.click()
    #                 await asyncio.sleep(2)
    #     except Exception as e:
    #         logger.debug(f"[{keyword}] Không có error box: {e}")

    @staticmethod
    async def _is_recent_item(item) -> bool:
        text = (await item.inner_text()).lower()
        return "ago" in text or "trước" in text

    @staticmethod
    async def _scroll_if_needed(page, index):
        if index >= 3 and (index - 3) % 4 == 0:
            await page.evaluate("window.scrollBy(0, 500)")
            await delay(800, 1200)

    @staticmethod
    async def _get_video_url(item):
        return await item.locator("a[href*='/video/']").get_attribute("href")

    @staticmethod
    async def _crawl_video(context, video_url):
        new_page = await context.new_page()

        try:
            await new_page.goto(video_url, wait_until="domcontentloaded")
            await delay(20000, 30000)

            video_info = await extract_video_info(new_page)
            return TiktokPost().new(video_info)

        finally:
            await new_page.close()

    @staticmethod
    async def _push_to_es(keyword, data):
        if not data:
            logger.info(f"[{keyword}] Không có dữ liệu hợp lệ")
            return

        try:
            result = await postToESUnclassified(data)
            if result.get("success"):
                logger.info(f"[{keyword}] ✅ ==============> ES OK: {result['total']}")
            else:
                logger.error(f"[{keyword}] ❌ ES fail: {result.get('error')}")
        except Exception as e:
            logger.error(f"[{keyword}] ❌ Lỗi push ES: {e}")