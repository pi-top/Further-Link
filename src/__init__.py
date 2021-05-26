import json

from aiohttp import web

from .ssl_context import ssl_context  # noqa: F401
from .apt_version import apt_version  # noqa: F401
from .run_py import run_py  # noqa: F401
from .run import run  # noqa: F401
from .lib.further_link import __version__


async def status(_):
    return web.Response(text='OK')


async def version(_):
    return web.Response(text=json.dumps({'version': __version__}))
