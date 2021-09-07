import os

import pytest
from src.util.message import create_message

from further_link import __version__

from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_use_lib(run_ws_client):
    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "stdout", "output", f"{__version__}\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
@pytest.mark.skipif("DISPLAY" not in os.environ, reason="requires UI")
async def test_use_display(run_ws_client):
    code = """\
from turtle import color
color('red')
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 5000, "1")


@pytest.mark.asyncio
async def test_keyevent(run_ws_client):
    code = """\
from further_link import KeyboardButton
from signal import pause
a = KeyboardButton('a')
b = KeyboardButton('b')
a.when_pressed = lambda: print('a pressed')
b.when_released = lambda: print('b released')
pause()
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, "started", process="1")
    await wait_for_data(run_ws_client, "keylisten", "output", "a", 0, "1")
    await wait_for_data(run_ws_client, "keylisten", "output", "b", 0, "1")

    await run_ws_client.send_str(
        create_message("keyevent", {"key": "a", "event": "keydown"}, "1")
    )

    await wait_for_data(run_ws_client, "stdout", "output", "a pressed\n", 0, "1")

    await run_ws_client.send_str(
        create_message("keyevent", {"key": "b", "event": "keyup"}, "1")
    )

    await wait_for_data(run_ws_client, "stdout", "output", "b released\n", 0, "1")

    await run_ws_client.send_str(create_message("stop", None, "1"))

    await wait_for_data(run_ws_client, "stopped", "exitCode", -15, 0, "1")


jpeg_pixel_b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"  # noqa: E501


@pytest.mark.asyncio
async def test_send_image_pil(run_ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_send_image_opencv(run_ws_client):
    code = """\
from numpy import array
from further_link import send_image
from PIL.Image import effect_noise
send_image(array(effect_noise((1, 1), 0)))
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_send_image_with_directory(run_ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message(
        "start", {"runner": "python3", "code": code, "directoryName": "my-dirname"}, "1"
    )
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")
