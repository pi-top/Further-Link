import asyncio
import functools
import logging
import os
import sys
from json import dumps

import aiohttp_cors
import click
from aiohttp import web

from further_link.endpoint.apt_version import apt_version
from further_link.endpoint.run import bt_run_handler
from further_link.endpoint.run import run as run_handler
from further_link.endpoint.run_py import run_py
from further_link.endpoint.upload import bt_upload, upload
from further_link.util import vnc
from further_link.util.bluetooth.device import BluetoothDevice, GattConfig
from further_link.util.bluetooth.gatt import (
    FURTHER_GATT_CONFIG,
    PT_RUN_CHARACTERISTIC_UUID,
    PT_RUN_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_UPLOAD_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
)
from further_link.util.ssl_context import ssl_context
from further_link.version import __version__

logging.basicConfig(
    stream=sys.stdout,
    level=(logging.DEBUG if os.environ.get("FURTHER_LINK_DEBUG") else logging.INFO),
)


def port():
    return int(os.environ.get("FURTHER_LINK_PORT", 8028))


def _status():
    return "OK"


def _version():
    return dumps({"version": __version__})


async def status(_):
    return web.Response(text=_status())


async def version(_):
    return web.Response(text=_version())


async def create_bluetooth_app():
    try:
        gatt_config = GattConfig("Further", FURTHER_GATT_CONFIG)
        gatt_config.register_read_handler(
            PT_RUN_SERVICE_UUID, PT_STATUS_CHARACTERISTIC_UUID, _status
        )
        gatt_config.register_read_handler(
            PT_RUN_SERVICE_UUID, PT_VERSION_CHARACTERISTIC_UUID, _version
        )
        gatt_config.register_write_handler(
            PT_RUN_SERVICE_UUID, PT_RUN_CHARACTERISTIC_UUID, bt_run_handler
        )
        gatt_config.register_write_handler(
            PT_RUN_SERVICE_UUID, PT_UPLOAD_CHARACTERISTIC_UUID, bt_upload
        )

        bt_iface = BluetoothDevice(gatt_config)
        await bt_iface.start()
        return bt_iface
    except Exception as e:
        logging.error(f"Error creating bluetooth device: {e}")


async def create_app():
    app = web.Application()

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

    exec_resource = cors.add(app.router.add_resource("/run-py"))
    cors.add(exec_resource.add_route("GET", run_py))

    exec_resource = cors.add(app.router.add_resource("/run"))
    cors.add(exec_resource.add_route("GET", run_handler))

    return app


def make_synchronous(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@make_synchronous
async def main():
    vnc.create_ssl_certificate()

    await create_bluetooth_app()

    app = await create_app()
    # Default handle_signals=True will ignore sigterm signals whilst there
    # are requests that are not complete. This isn't appropriate for our
    # indefinitely running websockets and can cause device shutdown to hang
    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    site = web.TCPSite(runner, port=port(), ssl_context=ssl_context())
    await site.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    main(prog_name="further-link")
