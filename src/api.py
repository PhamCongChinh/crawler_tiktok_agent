import os
import httpx

URL_UNCLASSIFIED = "http://103.97.125.64:4426/api/v1/posts/insert-unclassified-org-posts"

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
            print(f"Đã đẩy {total}")
            print(response)
        
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] Insert failed: {e.response.status_code} - {e.response.text}")
        return {"successes": 0, "errors": [{"error": str(e)}]}
    except Exception as e:
        print(f"[ERROR] Insert exception: {e}")
        return {"successes": 0, "errors": [{"error": str(e)}]}