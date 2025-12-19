import asyncio
import pytest
from app.utils_helper.threading import ThreadingUtils


@pytest.mark.asyncio
async def test_run_in_thread_executes():
    def add(a, b):
        return a + b

    res = await ThreadingUtils.run_in_thread(add, 2, 3)
    assert res == 5


def test_async_to_sync_runs():
    async def coro_mul(x):
        return x * 2

    wrapper = ThreadingUtils.async_to_sync(coro_mul)
    # call synchronously
    res = wrapper(3)
    assert res == 6
