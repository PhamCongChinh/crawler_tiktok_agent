import hashlib

class RedisDedupService:
    def __init__(self, redis_client, prefix="tiktok:video", ttl=86400):
        self.redis = redis_client
        self.prefix = prefix
        self.ttl = ttl

    def _key(self, value: str) -> str:
        h = hashlib.md5(value.encode()).hexdigest()
        return f"{self.prefix}:{h}"

    async def should_process(self, value: str) -> bool:
        key = self._key(value)
        ok = await self.redis.set(key, 1, nx=True, ex=self.ttl)
        return bool(ok)
