import asyncio
import os
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class ThreadingUtils:
    # Dynamic sizing: base workers on CPU count, capped to reasonable limits
    _cpu = os.cpu_count() or 1
    _max_workers = min(32, max(2, _cpu * 5))
    executor = ThreadPoolExecutor(max_workers=_max_workers)

    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ThreadingUtils.executor, lambda: func(*args, **kwargs)
        )

    @staticmethod
    def async_to_sync(func: Callable[..., Awaitable[T]]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(func(*args, **kwargs))

        return wrapper
