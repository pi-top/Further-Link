import asyncio
from collections import deque
from concurrent.futures import TimeoutError


async def loop_forever(*args, **kwargs):
    while True:
        await asyncio.sleep(1)


async def race(tasks, timeout=None):
    done, pending = await asyncio.wait(
        tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    if len(pending):
        await asyncio.wait(pending)
    return done


async def timeout(tasks, timeout):
    if not isinstance(tasks, list):
        tasks = [tasks]
    return await race(tasks, timeout)


async def stream_read(stream, chunk_size):
    try:
        return await stream.read(chunk_size)
    except OSError:
        pass  # probably stream was closed by end of process


async def ringbuf_read(
    stream,
    output_callback=None,
    done_condition=loop_forever,
    kBps=0,
):
    buffer_time = 0.1
    chunk_size = 256  # this is too large to support kBps < 3, that's ok
    max_chunks = None if kBps == 0 else int(kBps * buffer_time * 1000 / chunk_size)

    # stream is read into a ring buffer so that if produces faster desired
    # limit the oldest data is dumped
    # example limit 128kBps = 50 max_chunks * 256 byte chunk_size / 0.1s

    ringbuf = deque(maxlen=max_chunks)
    read_finished = asyncio.Event()

    async def read():
        process_done = asyncio.create_task(done_condition())
        read_data = None
        try:
            while True:
                if read_data is None:
                    read_data = asyncio.create_task(stream_read(stream, chunk_size))

                # never cancel a read in flight: a threaded file read (pty) that
                # is cancelled still consumes its bytes and they are lost
                await asyncio.wait(
                    [read_data, process_done], return_when=asyncio.FIRST_COMPLETED
                )

                if not read_data.done():
                    # process ended; let the pending read return what it wrote last
                    await asyncio.wait([read_data], timeout=buffer_time / 2)
                    if not read_data.done():
                        break

                result = read_data.result()
                read_data = None
                if not result:
                    break
                ringbuf.append(result)
        finally:
            for task in (read_data, process_done):
                if task and not task.done():
                    task.cancel()
            read_finished.set()

    async def write():
        while True:
            # let data buffer in ringbuf for buffer_time or until reading ends
            try:
                await asyncio.wait_for(read_finished.wait(), timeout=buffer_time)
            except (TimeoutError, asyncio.TimeoutError):
                pass

            data = b"".join(ringbuf)
            if data:
                ringbuf.clear()
                output = data.decode(encoding="utf-8")
                if output_callback:
                    await output_callback(output)
            if read_finished.is_set() and not ringbuf:
                break

    # write completes after read has finished and the ring buffer is flushed
    return await asyncio.wait(
        [asyncio.create_task(read()), asyncio.create_task(write())]
    )
