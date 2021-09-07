import json

from aiohttp import web

from .apt_version import apt_version  # noqa: F401
from .ipc import (  # noqa: F401
    async_ipc_send,
    async_start_ipc_server,
    ipc_cleanup,
    ipc_send,
    start_ipc_server,
)
from .keyboard_button import KeyboardButton  # noqa: F401
from .run import run  # noqa: F401
from .run_py import run_py  # noqa: F401
from .send_image import send_image  # noqa: F401
from .upload import upload  # noqa: F401
from .util.ssl_context import ssl_context  # noqa: F401
from .version import __version__  # noqa: F401


async def status(_):
    return web.Response(text="OK")


async def version(_):
    return web.Response(text=json.dumps({"version": __version__}))
