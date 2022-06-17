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
    buffer_time=0.1,
    max_chunks=50,
    chunk_size=256,
    done_condition=loop_forever,
):
    # stream is read into a ring buffer so that if produces faster desired
    # limit the oldest data is dumped
    # default limit ~ 50 * 256b / 0.1s (128k characters per second)

    ringbuf = deque(maxlen=max_chunks)
    completed = False

    async def read():
        nonlocal completed
        while True:
            read_data = asyncio.create_task(stream_read(stream, chunk_size))
            wait_done = asyncio.create_task(done_condition())

            done = await race([read_data, wait_done])

            if read_data not in done:
                completed = True
                break

            result = read_data.result()

            if result == b"":
                completed = True
                break

            ringbuf.append(read_data.result())

    async def write():
        nonlocal completed
        while True:
            # let data buffer in ringbuf for buffer_time or until process ends
            # if process ends ringbuf still needs to be handled
            try:
                await asyncio.wait_for(done_condition(), timeout=buffer_time)
                completed = True
            except (TimeoutError, asyncio.TimeoutError):
                pass

            data = b"".join(ringbuf)
            if data:
                ringbuf.clear()
                output = data.decode(encoding="utf-8")
                if output_callback:
                    await output_callback(output)
            if completed:
                break

    # when read is completed it will set a flag causing write to complete after
    # flushing a final time
    return await asyncio.wait(
        [asyncio.create_task(read()), asyncio.create_task(write())]
    )
