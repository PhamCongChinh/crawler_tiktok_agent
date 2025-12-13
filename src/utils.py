from datetime import datetime
import json
import random
import asyncio
import re

async def delay(min=2000, max=5000):
    await asyncio.sleep(random.uniform(min/1000, max/1000))


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

# def time_to_minutes(text: str) -> int | None:
#     text = text.lower()

#     m = re.search(r"(\d+)\s*(minute|minutes|hour|hours|day|days)\s*ago", text)
#     if m:
#         v, u = int(m.group(1)), m.group(2)
#         return v if "minute" in u else v * 60 if "hour" in u else v * 1440

#     m = re.search(r"(\d+)\s*(phút|giờ|ngày)\s*trước", text)
#     if m:
#         v, u = int(m.group(1)), m.group(2)
#         return v if u == "phút" else v * 60 if u == "giờ" else v * 1440

#     return None

def smart_delay():
    hour = datetime.now().hour
    if 1 <= hour <= 6:      # ban đêm
        return (800, 1500)
    return (1500, 3000)    # ban ngày

async def detect_captcha(page) -> bool:
    content = (await page.content()).lower()
    keywords = ["captcha", "verify", "human", "robot"]
    return any(k in content for k in keywords)