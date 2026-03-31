from datetime import datetime
from typing import Optional


class TiktokComment:

    BASE_URL = f"https://www.tiktok.com"
    crawl_source = 2
    crawl_source_code = 'tt'
    auth_type = 1
    source_type = 5
    crawl_bot = "tiktok-comment"

    @classmethod
    def _build_video_url(cls, unique_id: str, post_id: Optional[str]) -> str:
        """Tạo URL video TikTok"""
        if not post_id:
            return ""
        return f"{cls.BASE_URL}/@{unique_id}/video/{post_id}"
    

    @classmethod
    def _build_author_url(cls, unique_id: str) -> str:
        return f"{cls.BASE_URL}/@{unique_id}"

    @classmethod
    def new(cls, data: dict):

        unique_id = data.get("unique_id", None)
        comment_id = data.get("video_id", None)
        aweme_id = data.get("aweme_id", None)
        url = data.get("url", None)
        
        return {
            "doc_type": 2,
            "crawl_source": cls.crawl_source,
            "crawl_source_code": cls.crawl_source_code,
            "pub_time": data.get("pub_time", 0),
            "crawl_time": int(datetime.now().timestamp()),
            "subject_id": data.get("comment_id", None),
            "title": data.get("title", None),
            "description": data.get("description", None),
            "content": data.get("content"),
            # "url": self._build_video_url(url, aweme_id), # lấy url
            # "url": data.get("url", None),
            "url": "https://www.tiktok.com/@angiang_new/video/7623022972009205000",
            # "media_urls": data.get("media", "[]"),
            "media_urls": "[]",
            "comments": int(data.get("comments", 0) or 0),
            "shares": int(data.get("shares", 0) or 0),
            "reactions": int(data.get("reactions", 0) or 0),
            "favors": int(data.get("collectCount", 0) or 0),
            "views": int(data.get("views", 0) or 0),
            "web_tags": "[]",
            "web_keywords": "[]",
            "auth_id": data.get("auth_id", None),
            "auth_name": data.get("auth_name", None),
            "auth_type": cls.auth_type,
            "auth_url": cls._build_author_url(unique_id),
            "source_id": comment_id,
            "source_type": cls.source_type,
            "source_name": data.get("auth_name", None),
            # "source_url": cls._build_video_url(url, aweme_id),
            "source_url": "https://www.tiktok.com/@angiang_new/video/7623022972009205000",
            "reply_to": None,
            "level": None,
            "sentiment": 0,
            "isPriority": True,
            "crawl_bot": cls.crawl_bot,
            "org_id": data.get("org_id"),
            "source_ownership": "own"
        }