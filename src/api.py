import os
import httpx
from src.config.settings import settings
from src.db.mongo import MongoDB
db = MongoDB.get_db()
bot_config = db.tiktok_bot_configs
config = bot_config.find_one({"bot_name": settings.BOT_NAME})

URL_UNCLASSIFIED = f"{config['api_master']}/api/v1/posts/insert-unclassified-org-posts"

async def postToESUnclassified(content: any) -> any:
    total = len(content)
    data = {
        "index": "not_classify_org_posts",
        "data": content,
        "upsert": True
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(URL_UNCLASSIFIED, json=data)
            if response.status_code >= 400:
                return {
                    "success": False,
                    "total": total,
                    "status": response.status_code,
                    "error": response.text,
                    "response": None
                }
            return {
                "success": True,
                "total": total,
                "status": response.status_code,
                "error": None,
                "response": response.json()
            }
    except Exception as e:
        return {
            "success": False,
            "total": total,
            "status": None,
            "error": str(e),
            "response": None
        }