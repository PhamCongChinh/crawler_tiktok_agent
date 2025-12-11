import random
import asyncio

async def delay(min=2000, max=5000):
    await asyncio.sleep(random.uniform(min/1000, max/1000))