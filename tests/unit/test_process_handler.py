import asyncio
import getpass
import logging
import os
import sys
from asyncio.subprocess import Process

import pytest
from aiofiles.threadpool.binary import AsyncFileIO
from mock import AsyncMock

from further_link.runner.process_handler import ProcessHandler

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

    # is this too fast to even lookup the pgid?!
    # await p.start("echo 'hello\nworld'")

    await p.start("bash -c \"echo 'hello\nworld'\"")
    assert type(p.process) == Process
    p.on_start.assert_called()

    await p.process.wait()
    # takes some time to complete - there's a 0.1 sleep in there
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello\nworld\n")
    p.on_stop.assert_called_with(0)


@pytest.mark.asyncio
async def test_input():
    p = ProcessHandler(user)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    await p.start('python3 -c "print(input())"')
    p.on_start.assert_called()

    await p.send_input("hello\n")

    await p.process.wait()
    # takes some time to complete - there's a 0.1 sleep in there
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello\n")
    p.on_stop.assert_called_with(0)


@pytest.mark.asyncio
async def test_pty():
    p = ProcessHandler(user, pty=True)

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    await p.start('python3 -c "print(input())"')
    assert type(p.process) == Process
    assert p.pty
    assert type(p.pty_master) == AsyncFileIO
    assert type(p.pty_slave) == AsyncFileIO

    p.on_start.assert_called()

    await p.send_input("hello\n")

    await p.process.wait()
    # takes some time to complete - there's a 0.1 sleep in there
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with("stdout", "hello\r\nhello\r\n")
    p.on_stop.assert_called_with(0)
