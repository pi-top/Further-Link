import base64
import io
from datetime import datetime
from json import dumps
from shutil import copy
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from testpath import MockCommand

from further_link.util.bluetooth.uuids import (
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
)
from further_link.util.message import create_message

from ..dirs import WORKING_DIRECTORY
from . import E2E_PATH
from .helpers import send_formatted_bluetooth_message, wait_until
from .test_data.image import jpeg_pixel_b64


def message_received(message: bytearray, messages: list):
    def _message_received():
        for msg in messages:
            if msg.endswith(message):
                return True
        return False

    return _message_received


@pytest.mark.asyncio
async def test_run_code_script_with_directory(bluetooth_server):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message(
        "start",
        "1",
        {"runner": "python3", "code": code, "directoryName": "my-dirname"},
        "1",
    )

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    day = datetime.now().strftime("%A")
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{day}\r\n"},
            "client": "1",
            "process": "1",
        }
    )
    await wait_until(message_received(stdout_message.encode(), messages))

    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_run_code_relative_path(bluetooth_server):
    copy("{}/test_data/print_date.py".format(E2E_PATH), WORKING_DIRECTORY)
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message(
        "start", "1", {"runner": "python3", "path": "print_date.py"}, "1"
    )

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    day = datetime.now().strftime("%A")
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{day}\r\n"},
            "client": "1",
            "process": "1",
        }
    )
    await wait_until(message_received(stdout_message.encode(), messages))

    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_run_code_absolute_path(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message(
        "start",
        "1",
        {"runner": "python3", "path": "{}/test_data/print_date.py".format(E2E_PATH)},
        "1",
    )

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    day = datetime.now().strftime("%A")
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{day}\r\n"},
            "client": "1",
            "process": "1",
        }
    )
    await wait_until(message_received(stdout_message.encode(), messages))

    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


import getpass

current_user = getpass.getuser()


@pytest.mark.asyncio
async def test_runs_as_current_user(bluetooth_server):
    # as of now, we only support running as the current user
    code = """\
#!/bin/bash
whoami
sleep 1
"""
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message("start", "1", {"runner": "exec", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{current_user}\r\n"},
            "client": "1",
            "process": "1",
        }
    )

    for message in (
        b'{"type": "started", "data": null, "client": "1", "process": "1"}',
        stdout_message.encode(),
        b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
    ):
        await wait_until(message_received(message, messages))


@pytest.mark.asyncio
async def test_novnc(bluetooth_server):
    on_display_activity = None

    class MyVNCConnectionDetails:
        port = 8080
        path = "hello"

    # mock pt-web-vnc async_start
    screenshot_manager_mock = MagicMock()

    async def async_start_mock(*args, **kwargs):
        nonlocal on_display_activity
        on_display_activity = kwargs.get("on_display_activity")
        return screenshot_manager_mock

    async_start_mock = patch(
        "further_link.runner.process_handler.async_start", async_start_mock
    )
    async_start_mock.start()

    # decode the base64 sample image
    msg = base64.b64decode(jpeg_pixel_b64)
    buf = io.BytesIO(msg)
    img = Image.open(buf)

    code = """\
from time import sleep
sleep(1)
"""
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message(
        "start",
        "1",
        {"runner": "python3", "code": code, "novncOptions": {"enabled": True}},
        "1",
    )

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    with MockCommand.fixed_output("pt-web-vnc"):
        await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

        await wait_until(
            message_received(
                b'{"type": "started", "data": null, "client": "1", "process": "1"}',
                messages,
            )
        )

        # mock display activity
        await on_display_activity(MyVNCConnectionDetails)
        # screenshot manager returns an image
        screenshot_manager_mock.image = img

        novnc_message = dumps(
            {
                "type": "novnc",
                "data": {
                    "port": MyVNCConnectionDetails.port,
                    "path": MyVNCConnectionDetails.path,
                },
                "client": "1",
                "process": "1",
            }
        )
        await wait_until(message_received(novnc_message.encode(), messages))

        video_message = dumps(
            {
                "type": "video",
                "data": {"output": jpeg_pixel_b64},
                "client": "1",
                "process": "1",
            }
        )
        await wait_until(message_received(video_message.encode(), messages))

        await wait_until(
            message_received(
                b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
                messages,
            )
        )
