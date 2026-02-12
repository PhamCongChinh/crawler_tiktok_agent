import redis.asyncio as aioredis
# from src.config.settings import settings

# redis_client = aioredis.Redis(
#     host=settings.REDIS_HOST,
#     port=settings.REDIS_PORT,
#     db=settings.REDIS_DB,
#     password=settings.REDIS_PASSWORD
# )


redis_client = aioredis.Redis(
    host="localhost",
    port="6379",
    db="0",
    password=""
)

async def get_redis_client():
    return redis_client

async def close_redis_client():
    await redis_client.close()

async def ping_redis():
    return await redis_client.ping()