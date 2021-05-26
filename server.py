#!/usr/bin/python3

import os
import logging
import sys

from aiohttp import web
import aiohttp_cors

from src import ssl_context, status, version, apt_version, run_py, \
    run as run_handler

logging.basicConfig(
    stream=sys.stdout,
    level=(logging.DEBUG if os.environ.get('FURTHER_LINK_DEBUG')
           else logging.INFO)
)


def port():
    return int(os.environ.get('FURTHER_LINK_PORT', 8028))


def create_app():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        )
    })
    status_resource = cors.add(app.router.add_resource('/status'))
    cors.add(status_resource.add_route('GET', status))

    status_resource = cors.add(app.router.add_resource('/version/apt/{pkg}'))
    cors.add(status_resource.add_route('GET', apt_version))

    status_resource = cors.add(app.router.add_resource('/version'))
    cors.add(status_resource.add_route('GET', version))

    exec_resource = cors.add(app.router.add_resource('/run-py'))
    cors.add(exec_resource.add_route('GET', run_py))

    exec_resource = cors.add(app.router.add_resource('/run'))
    cors.add(exec_resource.add_route('GET', run_handler))

    return app


async def run_async():
    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, port=port(), ssl_context=ssl_context())
    await site.start()
    return runner


def run():
    return web.run_app(
        create_app(),
        port=port(),
        ssl_context=ssl_context(),
        # Default handle_signals=True will ignore sigterm signals whilst there
        # are requests that are not complete. This isn't appropriate for our
        # indefinitely running websockets and can cause device shutdown to hang
        handle_signals=False
    )


if __name__ == '__main__':
    run()
