from aiohttp import web

from .run_py import run_py


async def status(_):
    return web.Response(text='OK')
