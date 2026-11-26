"""Shared test helpers."""

import asyncio
from collections.abc import Callable


async def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    """Poll until `condition` is true; fail after `timeout`. Avoids fixed sleeps."""
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.005)
