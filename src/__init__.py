import os
import asyncio
from shutil import copy
import websockets

from .message import parse_message, create_message
from .process_handler import ProcessHandler

work_dir = os.environ.get("FURTHER_LINK_WORK_DIR", "/tmp")
lib = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(lib):
    file = os.path.join(lib, file_name)
    if os.path.isfile(os.path.join(lib, file)):
        copy(file, work_dir)


async def handle_message(message, process_handler):
    m_type, m_data = parse_message(message)
    if (m_type == 'start'
            and not process_handler.is_running()
            and 'sourceScript' in m_data
            and isinstance(m_data.get('sourceScript'), str)):
        await process_handler.start(m_data['sourceScript'])

    elif (m_type == 'stdin'
          and process_handler.is_running()
          and 'input' in m_data
          and isinstance(m_data.get('input'), str)):
        await process_handler.send_input(m_data['input'])

    elif (m_type == 'stop' and process_handler.is_running()):
        process_handler.stop()

    else:
        raise RuntimeError("bad message")


async def app(socket, path):
    async def on_start():
        await socket.send(create_message('started'))

    async def on_stop(exitCode):
        await socket.send(create_message('stopped', {'exitCode': exitCode}))

    async def on_output(channel, output):
        await socket.send(create_message(channel, {'output': output}))

    process_handler = ProcessHandler(
        on_start=on_start,
        on_stop=on_stop,
        on_output=on_output,
        work_dir=work_dir
    )
    bad_message_message = create_message('error', {'message': 'Bad message'})
    print('New connection', process_handler.id)

    try:
        async for message in socket:
            try:
                await handle_message(message, process_handler)
            except:
                await socket.send(bad_message_message)
    finally:
        print('Closed connection', id(socket))
        process_handler.stop()
