import asyncio
import json
import time

import urllib
from src.api import postToESUnclassified
from src.config.logging import setup_logging
import logging

from src.parsers.video_parser import TiktokPost
from src.utils import delay
setup_logging()
logger = logging.getLogger(__name__)

class CrawlerKeyword:

    @staticmethod
    async def crawler_keyword(context, page, keywords):
        logger.info(f"Đã tải {len(keywords)} từ khóa")
        await delay(2000, 4000)

        for keyword in keywords:
            logger.info(f"🔍 Bắt đầu crawl keyword: {keyword}")

            try:
                await CrawlerKeyword._crawl_single_keyword(
                    context=context,
                    page=page,
                    keyword=keyword
                )
            except Exception as e:
                logger.exception(f"[{keyword}] 🔥 Lỗi keyword")
                continue

            await delay(2000, 4000)

    # =======================

    @staticmethod
    async def _crawl_single_keyword(context, page, keyword: str):
        unix_time = int(time.time())
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.tiktok.com/search?q={encoded}&t={unix_time}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await delay(2000, 5000)

        await CrawlerKeyword._handle_search_error(page, keyword)

        locator = page.locator("[id^='grid-item-container-']")
        count = await locator.count()
        logger.info(f"[{keyword}] Có {count} tin bài")

        results = []

        for i in range(count):
            item = locator.nth(i)

            try:
                if not await CrawlerKeyword._is_recent_item(item):
                    continue

                await CrawlerKeyword._scroll_if_needed(page, i)

                video_url = await CrawlerKeyword._get_video_url(item)
                if not video_url:
                    continue

                logger.info(f"[{keyword}] [{i+1}] {video_url}")
                await delay(*smart_delay())

                post = await CrawlerKeyword._crawl_video(context, video_url)
                if post:
                    results.append(post)

            except Exception as e:
                logger.error(f"[{keyword}] ❌ Lỗi item {i}: {e}")

        await CrawlerKeyword._push_to_es(keyword, results)

    # =======================

    @staticmethod
    async def _handle_search_error(page, keyword):
        try:
            error_box = page.locator("h2[data-e2e='search-error-title']")
            if await error_box.is_visible():
                logger.warning(f"[{keyword}] ⚠️ Search error")
                btn = page.locator("button:has-text('Try again')")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
        except Exception as e:
            logger.debug(f"[{keyword}] Không có error box: {e}")

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
                logger.info(f"[{keyword}] ✅ ES OK: {result['total']}")
            else:
                logger.error(f"[{keyword}] ❌ ES fail: {result.get('error')}")
        except Exception as e:
            logger.error(f"[{keyword}] ❌ Lỗi push ES: {e}")