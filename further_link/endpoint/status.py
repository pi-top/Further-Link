from json import dumps

from aiohttp import web

from further_link.version import __version__


def raw_status():
    return "OK"


def raw_version():
    return dumps({"version": __version__})


async def status(_):
    return web.Response(text=raw_status())


async def version(_):
    return web.Response(text=raw_version())
