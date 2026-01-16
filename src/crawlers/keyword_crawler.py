import time
import urllib
from src.utils import delay, smart_delay

class KeywordCrawler:
    def __init__(self, context, redis_dedup, video_crawler, logger):
        self.context = context
        self.redis = redis_dedup
        self.video = video_crawler
        self.logger = logger

    async def crawl_keywords(self, page, keywords):
        for kw in keywords:
            await self._crawl_keyword(page, kw)
            await delay(20000, 40000)

    async def _crawl_keyword(self, page, keyword):
        url = self._build_search_url(keyword)
        await page.goto(url, wait_until="domcontentloaded")
        await delay(2000, 5000)

        await page.locator('#tabs-0-tab-search_video').click()
        await delay(2000, 5000)

        items = page.locator("[id^='grid-item-container-']")
        await self._scroll(page, items)

        count = await items.count()
        self.logger.info(f"[{keyword}] Tổng video: {count}")

        results = []
        recent_count = 0

        for i in range(count):
            item = items.nth(i)

            try:
                time_text = (await item.locator("time").inner_text()).strip()
            except:
                time_text = "unknown"

            if not await self._is_recent_item(item):
                    continue

            video_url = await self._get_video_url(item)
            if not video_url:
                continue

            if not await self.redis.should_process(video_url):
                self.logger.info(f"SKIP (cached): {video_url}")
                continue

            recent_count += 1
            self.logger.info(
                f"CRAWL [{recent_count}] {video_url} | ⏱ {time_text}"
            )

            post = await self.video.crawl(video_url)
            if post:
                results.append(post)

            await delay(10000, 15000)

        self.logger.info(f"[{keyword}] 🔥 Video mới trong recent: {recent_count}")
        if results:
            await self._push(keyword, results)

    def _build_search_url(self, keyword):
        encoded = urllib.parse.quote(keyword)
        return f"https://www.tiktok.com/search?q={encoded}"

    async def _scroll(self, page, locator):
        from src.utils import human_scroll
        await human_scroll(page, locator, times=5)

    async def _get_video_url(self, item):
        return await item.locator("a[href*='/video/']").get_attribute("href")
    
    @staticmethod
    async def _is_recent_item(item) -> bool:
        try:
            text = (await item.locator("time").inner_text()).lower()

            # Mới trong vài giờ / phút
            if any(x in text for x in ["minute", "phút", "hour", "giờ", "ago", "trước"]):
                return True

            # Gặp ngày là stop
            if any(x in text for x in ["day", "ngày", "week", "tuần"]):
                return False

            return True
        except:
            return True
