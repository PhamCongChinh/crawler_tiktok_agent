import asyncio
import socket
import httpx
import logging
from src.config.logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# BOT_ID = "bot-tiktok-1"
# BOT_NAME = "tiktok-hn1"
# BOT_TYPE = "tiktok"  # hoặc lấy từ config

API_HEALTH = "http://192.168.1.28:4420/api/v1/check/heartbeat"

async def heartbeat_loop(config: any):
    BOT_ID = config.get("bot_id", "")
    BOT_NAME = config.get("bot_name", "")
    BOT_TYPE = config.get("bot_type", "")
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(API_HEALTH, json={
                    "bot_id": BOT_ID,
                    "bot_name": BOT_NAME,
                    "bot_type": BOT_TYPE,
                    "records": 10
                })
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

        await asyncio.sleep(30)  # ping mỗi 30s