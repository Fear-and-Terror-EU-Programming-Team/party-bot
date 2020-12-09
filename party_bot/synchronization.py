"""
This module provides synchronization utilities to avoid race conditions.
"""

import asyncio


def synchronized(func, lock=None):
    """
    Function decorator that ensures that all functions decorated with this
    decorator are executed sequentially.

    Note that this function provides no guarantees regarding execution order.
    Two functions may execute in a different order than they were called.
    """

    func.__lock__ = lock or asyncio.Lock()

    async def synced_func(*args, **kws):
        async with func.__lock__:
            return await func(*args, **kws)

    synced_func.__name__ = func.__name__
    return synced_func
