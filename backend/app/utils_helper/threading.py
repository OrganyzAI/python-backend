import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
from functools import wraps


class ThreadingUtils:
    # Dynamic sizing: base workers on CPU count, capped to reasonable limits
    _cpu = os.cpu_count() or 1
    _max_workers = min(32, max(2, _cpu * 5))
    executor = ThreadPoolExecutor(max_workers=_max_workers)

    @staticmethod
    async def run_in_thread(func: Callable, *args, **kwargs) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ThreadingUtils.executor,
            lambda: func(*args, **kwargs)
        )

    @staticmethod
    def async_to_sync(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(func(*args, **kwargs))
        return wrapper
