import asyncio
import logging
import os
from typing import Optional

import aiohttp_cors
import click
from aiohttp import web

from further_link.endpoint.apt_version import apt_version
from further_link.endpoint.run import run as run_handler
from further_link.endpoint.status import status, version
from further_link.endpoint.upload import upload
from further_link.util import tls_bundle, vnc
from further_link.util.bluetooth.device import BluetoothDevice
from further_link.util.bluetooth.server import BluetoothServer
from further_link.util.ssl_context import active_not_after, ssl_context

logging.basicConfig()
logging.getLogger().setLevel(
    logging.DEBUG if os.environ.get("FURTHER_LINK_DEBUG") else logging.INFO
)


def port():
    return int(os.environ.get("FURTHER_LINK_PORT", 8028))


async def create_bluetooth_app() -> Optional[BluetoothServer]:
    if os.environ.get("FURTHER_LINK_SKIP_BLUETOOTH", "0").lower() in (
        "1",
        "true",
    ):
        return None

    bluetooth_server = None
    bluetooth_device = None
    try:
        bluetooth_device = await BluetoothDevice.create()
        bluetooth_server = BluetoothServer(bluetooth_device)
        await bluetooth_server.start()
    except Exception as e:
        logging.error(f"Error creating bluetooth device: {e}")
    return bluetooth_server


async def create_web_app():
    app = web.Application()

    async def set_extra_cors_headers(request, response):
        response.headers["Access-Control-Allow-Private-Network"] = "true"

    app.on_response_prepare.append(set_extra_cors_headers)

    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )

    status_resource = cors.add(app.router.add_resource("/status"))
    cors.add(status_resource.add_route("GET", status))

    status_resource = cors.add(app.router.add_resource("/version/apt/{pkg}"))
    cors.add(status_resource.add_route("GET", apt_version))

    status_resource = cors.add(app.router.add_resource("/version"))
    cors.add(status_resource.add_route("GET", version))

    status_resource = cors.add(app.router.add_resource("/upload"))
    cors.add(status_resource.add_route("POST", upload))

    exec_resource = cors.add(app.router.add_resource("/run"))
    cors.add(exec_resource.add_route("GET", run_handler))

    return app


def tls_updates(context):
    async def run_in_background(app):
        task = asyncio.create_task(
            tls_bundle.keep_updated(
                context, active_not_after(), vnc.create_ssl_certificate
            )
        )
        yield
        task.cancel()

    return run_in_background


async def create_app(context=None):
    await create_bluetooth_app()
    app = await create_web_app()
    if context is not None:
        app.cleanup_ctx.append(tls_updates(context))
    return app


@click.command()
def main():
    context = ssl_context()
    vnc.create_ssl_certificate()
    return web.run_app(
        create_app(context),
        port=port(),
        ssl_context=context,
        # Default handle_signals=True will ignore sigterm signals whilst there
        # are requests that are not complete. This isn't appropriate for our
        # indefinitely running websockets and can cause device shutdown to hang
        handle_signals=False,
    )


if __name__ == "__main__":
    main(prog_name="further-link")
