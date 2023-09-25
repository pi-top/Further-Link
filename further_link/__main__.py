import logging
import os
import sys
from typing import Optional

import aiohttp_cors
import click
from aiohttp import web

from further_link.endpoint.apt_version import apt_version, apt_version_bt
from further_link.endpoint.run import bluetooth_run_handler
from further_link.endpoint.run import run as run_handler
from further_link.endpoint.run_py import run_py
from further_link.endpoint.status import raw_status, raw_version, status, version
from further_link.endpoint.upload import bluetooth_upload, upload
from further_link.util import vnc
from further_link.util.bluetooth.gatt import (
    FURTHER_GATT_CONFIG,
    PT_APT_VERSION_READ_CHARACTERISTIC_UUID,
    PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_UPLOAD_READ_CHARACTERISTIC_UUID,
    PT_UPLOAD_WRITE_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.server import BluetoothServer, GattConfig
from further_link.util.ssl_context import ssl_context

logging.basicConfig(
    stream=sys.stdout,
    level=(logging.DEBUG if os.environ.get("FURTHER_LINK_DEBUG") else logging.INFO),
)


def port():
    return int(os.environ.get("FURTHER_LINK_PORT", 8028))


async def create_bluetooth_app() -> Optional[BluetoothServer]:
    bluetooth_device = None
    try:
        # Associate characteristic read/write with handlers
        # 'upload' and 'run' features use 2 characteristics; one ('READ') is used by the client to read the
        # characteristic's value, or get notified of a change in the characteristic's value when subscribed.
        #
        # The other ('WRITE') is used by the client to send a value to the server.
        #
        # When a value is written to the 'WRITE' characteristic, the associated callback will be executed,
        # writing a value to the associated 'READ' characteristic.
        #
        # In both cases, the value written/read from/to the characteristic is treated as a message being sent/received.
        gatt_config = GattConfig("Further", FURTHER_GATT_CONFIG)
        gatt_config.register_read_handler(
            PT_SERVICE_UUID, PT_STATUS_CHARACTERISTIC_UUID, raw_status
        )
        gatt_config.register_read_handler(
            PT_SERVICE_UUID, PT_VERSION_CHARACTERISTIC_UUID, raw_version
        )
        gatt_config.register_write_handler(
            PT_SERVICE_UUID,
            PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
            lambda device, uuid, message: apt_version_bt(
                device, uuid, message, PT_APT_VERSION_READ_CHARACTERISTIC_UUID
            ),
        )
        gatt_config.register_write_handler(
            PT_SERVICE_UUID,
            PT_RUN_WRITE_CHARACTERISTIC_UUID,
            lambda device, uuid, message: bluetooth_run_handler(
                device, uuid, message, PT_RUN_READ_CHARACTERISTIC_UUID
            ),
        )
        gatt_config.register_write_handler(
            PT_SERVICE_UUID,
            PT_UPLOAD_WRITE_CHARACTERISTIC_UUID,
            lambda device, uuid, message: bluetooth_upload(
                device, uuid, message, PT_UPLOAD_READ_CHARACTERISTIC_UUID
            ),
        )

        bluetooth_device = BluetoothServer(gatt_config)
        await bluetooth_device.start()
    except Exception as e:
        logging.error(f"Error creating bluetooth device: {e}")
    return bluetooth_device


async def create_web_app():
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


async def create_app():
    await create_bluetooth_app()
    app = await create_web_app()
    return app


@click.command()
def main():
    vnc.create_ssl_certificate()
    return web.run_app(
        create_app(),
        port=port(),
        ssl_context=ssl_context(),
        # Default handle_signals=True will ignore sigterm signals whilst there
        # are requests that are not complete. This isn't appropriate for our
        # indefinitely running websockets and can cause device shutdown to hang
        handle_signals=False,
    )


if __name__ == "__main__":
    main(prog_name="further-link")
