import random
import asyncio
from datetime import datetime, time as dtime, timedelta
from typing import Optional


class SleepManager:
    def __init__(self, logger):
        self.logger = logger
        self._sleep_start: Optional[dtime] = None
        self._sleep_end: Optional[dtime] = None
        self._date = None

    def _generate_today_sleep_time(self) -> None:
        today = datetime.now().date()

        # random giờ ngủ 00:00 – 01:00
        sleep_minute = random.randint(0, 59)

        # random giờ thức 06:00 – 07:00
        wake_minute = random.randint(0, 59)

        self._sleep_start = dtime(0, sleep_minute)
        self._sleep_end   = dtime(6, wake_minute)
        self._date        = today

        self.logger.info(
            f"🌙 Sleep window today: {self._sleep_start} → {self._sleep_end}"
        )

    def is_sleep_time(self) -> bool:
        now = datetime.now()

        if self._date != now.date():
            self._generate_today_sleep_time()

        current = now.time()
        return self._sleep_start <= current < self._sleep_end

    async def sleep_until_wakeup(self) -> None:
        if self._sleep_end is None:
            self._generate_today_sleep_time()

        now = datetime.now()

        wake_datetime = now.replace(
            hour=self._sleep_end.hour,
            minute=self._sleep_end.minute,
            second=0,
            microsecond=0,
        )

        if now.time() >= self._sleep_end:
            wake_datetime += timedelta(days=1)

        seconds = (wake_datetime - now).total_seconds()

        self.logger.info(f"😴 Sleeping {seconds/3600:.2f} hours...")
        await asyncio.sleep(seconds)