import asyncio

import pytest

from further_link.util.bluetooth.uuids import (
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
)
from further_link.util.message import append_to_message, create_message

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
async def test_fails_if_no_client_uuid_is_provided(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    await wait_until(lambda: len(messages) > 0)
    assert messages[0].endswith(b"Error: client_uuid not provided in message")


@pytest.mark.asyncio
async def test_use_lib(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "1"})

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await asyncio.sleep(1)

    await wait_until(lambda: len(messages) == 3)
    message_end = [
        b'{"type": "started", "data": null, "process": "1"}',
        b'{"type": "stdout", "data": {"output": "0.0.1.dev1\\n"}, "process": "1"}',
        b'{"type": "stopped", "data": {"exitCode": 0}, "process": "1"}',
    ]
    for message, message_end in zip(messages, message_end):
        assert message.endswith(message_end)


@pytest.mark.asyncio
async def test_keyevent(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from further_link import KeyboardButton
from signal import pause
a = KeyboardButton('a')
b = KeyboardButton('b')
a.when_pressed = lambda: print('a pressed')
b.when_released = lambda: print('b released')
pause()
"""

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "2")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "2"})
    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )

    await wait_until(lambda: len(messages) == 3)
    message_end = [
        b'{"type": "started", "data": null, "process": "2"}',
        b'{"type": "keylisten", "data": {"output": "a"}, "process": "2"}',
        b'{"type": "keylisten", "data": {"output": "b"}, "process": "2"}',
    ]
    for message, message_end in zip(messages, message_end):
        assert message.endswith(message_end)

    # send keyevent and wait for output
    start_cmd = create_message("keyevent", {"key": "a", "event": "keydown"}, "2")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "2"})
    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )

    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "a pressed\\n"}, "process": "2"}',
            messages,
        )
    )

    # send keyevent and wait for output
    start_cmd = create_message("keyevent", {"key": "b", "event": "keyup"}, "2")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "2"})
    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )
    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "b released\\n"}, "process": "2"}',
            messages,
        )
    )

    # send stop message and wait for response
    start_cmd = create_message("stop", None, "2")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "2"})
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": -15}, "process": "2"}', messages
        )
    )


@pytest.mark.asyncio
async def test_send_image_pil(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    start_cmd = create_message("start", {"runner": "python3", "code": code}, "3")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "3"})
    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )

    await wait_until(lambda: len(messages) == 3)
    message_end = [
        b'{"type": "started", "data": null, "process": "3"}',
        b'{"type": "video", "data": {"output": "'
        + jpeg_pixel_b64.encode()
        + b'"}, "process": "3"}',
        b'{"type": "stopped", "data": {"exitCode": 0}, "process": "3"}',
    ]
    for message, message_end in zip(messages, message_end):
        assert message.endswith(message_end)


@pytest.mark.asyncio
async def test_send_image_opencv(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    code = """\
from numpy import array
from further_link import send_image
from PIL.Image import effect_noise
send_image(array(effect_noise((1, 1), 0)))
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "4")
    start_cmd = append_to_message(start_cmd, {"client_uuid": "4"})

    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )
    await wait_until(lambda: len(messages) == 3)
    message_end = [
        b'{"type": "started", "data": null, "process": "4"}',
        b'{"type": "video", "data": {"output": "/9j/4AAQSkZJRgABAQAAAQABAA'
        + b"D/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIx"
        + b"wcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAA"
        + b'AAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"}, "p'
        + b'rocess": "4"}',
        b'{"type": "stopped", "data": {"exitCode": 0}, "process": "4"}',
    ]
    for message, message_end in zip(messages, message_end):
        assert message.endswith(message_end)


@pytest.mark.asyncio
async def test_send_image_with_directory(bluetooth_server):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    start_cmd = create_message(
        "start", {"runner": "python3", "code": code, "directoryName": "my-dirname"}, "5"
    )
    start_cmd = append_to_message(start_cmd, {"client_uuid": "5"})

    await send_formatted_bluetooth_message(
        bluetooth_server,
        char,
        start_cmd,
    )
    await wait_until(lambda: len(messages) == 3)
    message_end = [
        b'{"type": "started", "data": null, "process": "5"}',
        b'{"type": "video", "data": {"output": "/9j/4AAQSkZJRgABAQAAAQABAA'
        b"D/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIx"
        b"wcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAA"
        b'AAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"}, "p'
        b'rocess": "5"}',
        b'{"type": "stopped", "data": {"exitCode": 0}, "process": "5"}',
    ]
    for message, message_end in zip(messages, message_end):
        assert message.endswith(message_end)
