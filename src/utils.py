from datetime import datetime
import random
import asyncio
import json

async def delay(min=2000, max=5000):
    await asyncio.sleep(random.uniform(min/1000, max/1000))

def smart_delay():
    hour = datetime.now().hour
    if 1 <= hour <= 6:      # ban đêm
        return (2800, 7500)
    return (4000, 8000)    # ban ngày

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