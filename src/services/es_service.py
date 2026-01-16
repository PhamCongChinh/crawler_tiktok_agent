from src.api import postToESUnclassified

class ESService:
    async def push(self, keyword, data, logger):
        if not data:
            return
        result = await postToESUnclassified(data)
        if result.get("success"):
            logger.info(f"[{keyword}] ES OK: {result['total']}")
        else:
            logger.error(f"[{keyword}] ES fail")
