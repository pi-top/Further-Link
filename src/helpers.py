import asyncio
from collections import deque


async def loop_forever(*args, **kwargs):
    while True:
        await asyncio.sleep(1)
        pass


async def race(tasks):
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    await asyncio.wait(pending)
    return done


async def ringbuf_read(
    stream,
    output_callback=None,
    buffer_time=0.1,
    max_chunks=50,
    chunk_size=256,
    done_condition=loop_forever
):
    # stream is read into a ring buffer so that if produces faster desired
    # limit the oldest data is dumped
    # default limit ~ 50 * 256b / 0.1s (128k characters per second)

    ringbuf = deque(maxlen=max_chunks)

    async def read():
        while True:
            read_data = asyncio.create_task(stream.read(chunk_size))
            wait_done = asyncio.create_task(done_condition())

            done = await race([read_data, wait_done])

            if read_data not in done:
                break

            result = read_data.result()
            if result == b'':
                break

            ringbuf.append(read_data.result())

    async def write():
        while True:
            # let data buffer in ringbuf for buffer_time or until process ends
            # if process ends ringbuf still needs to be handled
            done = False
            try:
                await asyncio.wait_for(done_condition(), timeout=buffer_time)
                done = True
            except asyncio.TimeoutError:
                pass

            data = b''.join(ringbuf)
            if data:
                ringbuf.clear()
                output = data.decode(encoding='utf-8')
                if output_callback:
                    await output_callback(output)
            if done:
                break

    await race([
        asyncio.create_task(read()),
        asyncio.create_task(write())
    ])
