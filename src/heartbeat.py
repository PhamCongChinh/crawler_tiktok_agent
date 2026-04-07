import asyncio
import socket
import httpx
import logging
from src.config.logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

BOT_ID = socket.gethostname()
BOT_TYPE = "tiktok"  # hoặc lấy từ config

API_HEALTH = "http://192.168.1.28:4420/api/v1/check/heartbeat"

async def heartbeat_loop():
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(API_HEALTH, json={
                    "bot_id": BOT_ID,
                    "bot_type": BOT_TYPE,
                    "records": 0
                })
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

        await asyncio.sleep(30)  # ping mỗi 30s