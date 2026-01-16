from src.parsers.video_parser import TiktokPost
from src.utils import extract_video_info, delay

class VideoCrawler:
    def __init__(self, page_manager):
        self.pm = page_manager

    async def crawl(self, video_url):
        page = await self.pm.new_page()
        try:
            await page.goto(video_url, wait_until="domcontentloaded")
            await delay(20000, 30000)
            info = await extract_video_info(page)
            return TiktokPost().new(info)
        finally:
            await page.close()
