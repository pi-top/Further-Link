import asyncio
from functools import partial
from json import dumps
from time import sleep

from aiohttp import web

from ..util.async_helpers import timeout
from ..util.id_generator import id_generator
from ..version import __version__


async def status(_):
    return web.Response(text="OK")


async def version(_):
    return web.Response(text=dumps({"version": __version__}))


async def live(_):
    if not id_generator.has_ids():
        raise Exception("All ids are in use.")

    async_task = asyncio.create_task(asyncio.sleep(0.1))
    done = await timeout(async_task, 0.2)
    if async_task not in done:
        raise Exception("Async coroutines blocked.")

    sleep_thread = asyncio.to_thread(partial(sleep, 0.1))
    async_thread_task = asyncio.create_task(sleep_thread)
    done = await timeout(async_thread_task, 0.2)
    if async_thread_task not in done:
        raise Exception("Async threads blocked.")

    return web.Response(text="OK")
