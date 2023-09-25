import asyncio
import json

import pytest

from further_link.util.bluetooth.gatt import (
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
)
from further_link.util.bluetooth.messages import ChunkedMessage
from further_link.util.message import create_message


async def send_long_message(
    client, characteristic, message, assert_characteristic_value=True
):
    if not isinstance(message, str):
        message = json.dumps(message)
    chunked_message = ChunkedMessage.from_long_message(message)

    for i in range(chunked_message.total_chunks):
        chunk = chunked_message.chunk(i)

        # send chunk to server
        client.server.write(characteristic, chunk)

        # read characteristic value and confirm it's the same message as the one sent
        if assert_characteristic_value:
            assert client.read_value(characteristic.uuid) == chunk


async def wait_until_value_is(client, characteristic_uuid, value, timeout=5):
    elapsed = 0.0
    delta_t = 0.1
    while client.read_value(characteristic_uuid) != value and elapsed < timeout:
        await asyncio.sleep(delta_t)
        elapsed += delta_t

    if elapsed >= timeout:
        raise TimeoutError(
            f"Timed out waiting for {value} on characteristic {characteristic_uuid}; read '{client.read_value(characteristic_uuid)}'"
        )


@pytest.mark.asyncio
async def test_use_lib(bluetooth_client):
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_RUN_WRITE_CHARACTERISTIC_UUID
    )

    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")

    messages = []
    bluetooth_client.server._subscribe_to_characteristic(
        PT_RUN_READ_CHARACTERISTIC_UUID, lambda msg: messages.append(msg)
    )

    await send_long_message(bluetooth_client, char, start_cmd)
    await asyncio.sleep(2)

    expected_messages = [
        bytearray(b'{"type": "started", "data": null, "process": "1"}'),
        bytearray(
            b'{"type": "stdout", "data": {"output": "0.0.1.dev1\\n"}, "process": "1"}'
        ),
        bytearray(b'{"type": "stopped", "data": {"exitCode": 0}, "process": "1"}'),
    ]
    for msg, expected in zip(messages, expected_messages):
        assert msg == expected


@pytest.mark.skip(reason="fails on button press/release event")
@pytest.mark.asyncio
async def test_keyevent(bluetooth_client):
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_RUN_WRITE_CHARACTERISTIC_UUID
    )

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
    bluetooth_client.server._subscribe_to_characteristic(
        PT_RUN_READ_CHARACTERISTIC_UUID, lambda msg: messages.append(msg)
    )

    await send_long_message(
        bluetooth_client,
        char,
        create_message("start", {"runner": "python3", "code": code}, "1"),
    )
    await asyncio.sleep(2)

    for index, expected_message in enumerate(
        [
            bytearray(b'{"type": "started", "data": null, "process": "1"}'),
            bytearray(
                b'{"type": "keylisten", "data": {"output": "a"}, "process": "1"}'
            ),
            bytearray(
                b'{"type": "keylisten", "data": {"output": "b"}, "process": "1"}'
            ),
        ]
    ):
        assert expected_message == messages[index]

    await send_long_message(
        bluetooth_client,
        char,
        create_message("keyevent", {"key": "a", "event": "keydown"}, "1"),
    )
    await asyncio.sleep(2)
    assert messages[-1] == bytearray(
        b'{"type": "stdout", "data": {"output": "a pressed\\n"}, "process": "1"}'
    )

    await send_long_message(
        bluetooth_client,
        char,
        create_message("keyevent", {"key": "b", "event": "keyup"}, "1"),
    )
    await asyncio.sleep(2)
    assert messages[-1] == bytearray(
        b'{"type": "stdout", "data": {"output": "b released\\n"}, "process": "1"}'
    )

    await send_long_message(bluetooth_client, char, create_message("stop", None, "1"))
    await asyncio.sleep(2)
    assert messages[-1] == 1


jpeg_pixel_b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"  # noqa: E501


@pytest.mark.skip("fails")
@pytest.mark.asyncio
async def test_send_image_pil(bluetooth_client):
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_RUN_WRITE_CHARACTERISTIC_UUID
    )

    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""

    messages = []
    bluetooth_client.server._subscribe_to_characteristic(
        PT_RUN_READ_CHARACTERISTIC_UUID, lambda msg: messages.append(msg)
    )

    await send_long_message(
        bluetooth_client,
        char,
        create_message("start", {"runner": "python3", "code": code}, "1"),
    )

    await asyncio.sleep(2)
    assert messages == ""

    for index, expected_message in enumerate([]):
        assert expected_message == messages[index]


# @pytest.mark.asyncio
# async def test_send_image_opencv(run_ws_client):
#     code = """\
# from numpy import array
# from further_link import send_image
# from PIL.Image import effect_noise
# send_image(array(effect_noise((1, 1), 0)))
# """
#     start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
#     await run_ws_client.send_str(start_cmd)

#     await wait_for_data(run_ws_client, "started", process="1")

#     await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

#     await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


# @pytest.mark.asyncio
# async def test_send_image_with_directory(run_ws_client):
#     code = """\
# from further_link import send_image
# from PIL.Image import effect_noise
# send_image(effect_noise((1, 1), 0))
# """
#     start_cmd = create_message(
#         "start", {"runner": "python3", "code": code, "directoryName": "my-dirname"}, "1"
#     )
#     await run_ws_client.send_str(start_cmd)

#     await wait_for_data(run_ws_client, "started", process="1")

#     await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

#     await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")
