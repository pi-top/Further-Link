import json

from aiohttp import web

from .apt_version import apt_version  # noqa: F401
from .run_py import run_py  # noqa: F401
from .run import run  # noqa: F401
from .upload import upload  # noqa: F401
from .lib.further_link import __version__
from .util.ssl_context import ssl_context  # noqa: F401


async def status(_):
    return web.Response(text='OK')


async def version(_):
    return web.Response(text=json.dumps({'version': __version__}))
