import asyncio
from functools import partial
from time import time

import pytest
from mock import AsyncMock

from further_link.util.async_helpers import race, ringbuf_read, timeout


@pytest.mark.asyncio
async def test_race():
    quick_task = asyncio.create_task(asyncio.sleep(0.1))
    slow_task = asyncio.create_task(asyncio.sleep(1))
    done = await race([quick_task, slow_task])
    assert len(done) == 1
    assert quick_task in done
    assert quick_task.done()
    assert slow_task.cancelled()


@pytest.mark.asyncio
async def test_timeout_early():
    start_time = time()
    task_time = 0.1
    timeout_time = 1

    short_task = asyncio.create_task(asyncio.sleep(task_time))
    await timeout(short_task, timeout_time)

    duration = time() - start_time

    assert short_task.done()
    assert duration > 0.1
    assert duration < 0.2


@pytest.mark.asyncio
async def test_timeout_timedout():
    start_time = time()
    task_time = 1
    timeout_time = 0.1

    long_task = asyncio.create_task(asyncio.sleep(task_time))
    await timeout(long_task, timeout_time)

    duration = time() - start_time

    assert long_task.cancelled()
    assert duration > 0.1
    assert duration < 0.2


@pytest.mark.asyncio
async def test_ringbuf_read():
    buffer_time = 0.1
    max_chunks = 10
    chunk_size = 10

    bytes_buffered = max_chunks * chunk_size
    fast_stream = asyncio.StreamReader()
    fast_stream.feed_data(b"a" * bytes_buffered + b"b" * bytes_buffered)

    read_callback = AsyncMock()

    ringbuf_read_task = asyncio.create_task(
        ringbuf_read(
            fast_stream,
            read_callback,
            buffer_time=buffer_time,
            max_chunks=max_chunks,
            chunk_size=chunk_size,
        )
    )
    await asyncio.sleep(buffer_time + 0.01)

    # first 100 bytes of 'a's should be dropped
    read_callback.assert_called_with("b" * bytes_buffered)

    fast_stream.feed_eof()
    await asyncio.sleep(buffer_time + 0.01)
    assert ringbuf_read_task.done()


@pytest.mark.asyncio
async def test_ringbuf_read_done_condition():
    fast_stream = asyncio.StreamReader()
    fast_stream.feed_data(b"hello")
    buffer_time = 0.1
    done_time = 0.3

    read_callback = AsyncMock()

    ringbuf_read_task = asyncio.create_task(
        ringbuf_read(
            fast_stream,
            read_callback,
            buffer_time=buffer_time,
            done_condition=partial(asyncio.sleep, done_time),
        )
    )
    await asyncio.sleep(buffer_time + 0.01)

    read_callback.assert_called_with("hello")
    await asyncio.sleep(done_time - buffer_time)
    assert ringbuf_read_task.done()
