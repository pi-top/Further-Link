import asyncio
import getpass
import logging
import os
import sys
from asyncio.subprocess import Process
from base64 import b64decode
from io import BytesIO
from unittest.mock import patch

import pytest
from aiofiles.threadpool.binary import AsyncFileIO
from mock import AsyncMock
from PIL import Image

from further_link.runner.process_handler import ProcessHandler
from further_link.util.vnc import VNC_CERTIFICATE_PATH

logging.basicConfig(
    stream=sys.stdout,
    level=(logging.DEBUG if os.environ.get("FURTHER_LINK_DEBUG") else logging.INFO),
)

user = getpass.getuser()


@pytest.mark.asyncio
async def test_basic():
    p = ProcessHandler(user)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    # this is fast, won't have time to get it's pgid and set up ipc, but we
    # should get the output still
    await p.start("echo 'hello world'")

    assert type(p.process) == Process
    p.on_start.assert_called()

    await p.process.wait()
    # takes some time to flush - 0.1s output buffer etc
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello world\n")
    p.on_stop.assert_called_with(0)


@pytest.mark.asyncio
async def test_input():
    p = ProcessHandler(user)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    await p.start('python3 -u -c "print(input())"')
    p.on_start.assert_called()

    await p.send_input("hello\n")

    await p.process.wait()
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello\n")
    p.on_stop.assert_called_with(0)


@pytest.mark.asyncio
async def test_pty():
    p = ProcessHandler(user, pty=True)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    await p.start('python3 -u -c "print(input())"')
    assert type(p.process) == Process
    assert p.pty
    assert type(p.pty_master) == AsyncFileIO
    assert type(p.pty_slave) == AsyncFileIO

    p.on_start.assert_called()

    await p.send_input("hello\n")

    await p.process.wait()
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello\r\nhello\r\n")
    p.on_stop.assert_called_with(0)


@pytest.mark.asyncio
async def test_novnc():
    p = ProcessHandler(user)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()
    p.on_display_activity = AsyncMock()

    code = """\
from signal import pause
print('doing fake graphics!')
pause()
"""
    novncOptions = {"enabled": True, "height": 620, "width": 780}

    with patch(
        "further_link.runner.process_handler.async_start", AsyncMock()
    ) as vnc_start:
        jpeg_pixel_b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"  # noqa: E501
        vnc_start.return_value.image = Image.open(BytesIO(b64decode(jpeg_pixel_b64)))

        await p.start(f'python3 -u -c "{code}"', novncOptions=novncOptions)

        vnc_start.assert_called_with(
            display_id=p.id,
            on_display_activity=p.on_display_activity,
            ssl_certificate=VNC_CERTIFICATE_PATH,
            with_window_manager=True,
            height=novncOptions.get("height"),
            width=novncOptions.get("width"),
            screenshot_timeout=1,
        )

    p.on_start.assert_called()

    await asyncio.sleep(0.2)
    p.on_output.assert_called_with("stdout", "doing fake graphics!\n")

    with patch(
        "further_link.runner.process_handler.async_stop", AsyncMock()
    ) as vnc_stop:
        await p.stop()
        await p.process.wait()
        await asyncio.sleep(0.2)

        vnc_stop.assert_called_with(p.id)

    p.on_output.assert_called_with("video", jpeg_pixel_b64)

    p.on_stop.assert_called_with(-15)
