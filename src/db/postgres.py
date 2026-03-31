import asyncpg

from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))

import os
from dotenv import load_dotenv

load_dotenv()

class PostgresDB:
    pool = None
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                database=os.getenv("POSTGRES_DB", "postgres"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                min_size=10,
                max_size=50,   # tăng nếu crawl mạnh
                command_timeout=60
            )
            print("✅ Connected PostgreSQL")

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("❌ Closed PostgreSQL")

    async def fetch_posts(self, limit=10):
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())
        start, end = self.get_day_range(now_ts)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, org_id, url
                FROM tbl_posts
                WHERE crawl_source_code = 'tt'
                AND pub_time >= $1
                AND pub_time < $2
                ORDER BY id DESC
                LIMIT $3
            """, 1774762609, end, limit)
            return [dict(row) for row in rows]
        
    def get_day_range(self, ts: int):
        # dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        # start = int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp())
        # end = start + 86400
        # return start, end
        dt = datetime.fromtimestamp(ts, tz=VN_TZ)
        start = int(datetime(dt.year, dt.month, dt.day, tzinfo=VN_TZ).timestamp())
        end = start + 86400
        return start, end