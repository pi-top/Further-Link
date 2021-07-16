import pytest
import os
import logging
import sys
import asyncio
from mock import AsyncMock

from src.process_handler import ProcessHandler

logging.basicConfig(
    stream=sys.stdout,
    level=(logging.DEBUG if os.environ.get('FURTHER_LINK_DEBUG')
           else logging.INFO)
)


@pytest.mark.asyncio
async def test_process_handler():
    p = ProcessHandler(os.environ.get('USER'))

    p.on_start = AsyncMock()
    p.on_stop = AsyncMock()
    p.on_output = AsyncMock()

    # is this too fast to even lookup the pgid?!
    # await p.start("echo 'hello\nworld'")

    await p.start("bash -c \"echo 'hello\nworld'\"")
    p.on_start.assert_called()

    await p.process.wait()
    # takes some time to complete - there's a 0.1 sleep in there
    await asyncio.sleep(0.2)

    p.on_output.assert_called_with('stdout', 'hello\nworld\n')
    p.on_stop.assert_called_with(0)
