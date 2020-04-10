import os
import asyncio
from shutil import copy

from aiohttp import web, WSMsgType

from .message import parse_message, create_message, BadMessage
from .py_process_handler import PyProcessHandler, InvalidOperation

WORK_DIR = os.environ.get('FURTHER_LINK_WORK_DIR', '/tmp')
LIB = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(LIB):
    file = os.path.join(LIB, file_name)
    if os.path.isfile(os.path.join(LIB, file)):
        copy(file, WORK_DIR)


async def handle_message(message, process_handler):
    m_type, m_data = parse_message(message)

    if (m_type == 'start'
            and 'sourceScript' in m_data
            and isinstance(m_data.get('sourceScript'), str)):
        await process_handler.start(m_data['sourceScript'])

    elif (m_type == 'stdin'
          and 'input' in m_data
          and isinstance(m_data.get('input'), str)):
        await process_handler.send_input(m_data['input'])

    elif m_type == 'stop':
        process_handler.stop()

    else:
        raise BadMessage()


async def run_py(request):
    socket = web.WebSocketResponse()
    await socket.prepare(request)

    async def on_start():
        await socket.send_str(create_message('started'))
        print('Started', process_handler.id)

    async def on_stop(exit_code):
        await socket.send_str(create_message('stopped', {'exitCode': exit_code}))
        print('Stopped', process_handler.id)

    async def on_output(channel, output):
        await socket.send_str(create_message(channel, {'output': output}))

    process_handler = PyProcessHandler(
        on_start=on_start,
        on_stop=on_stop,
        on_output=on_output,
        work_dir=WORK_DIR
    )
    print('New connection', process_handler.id)

    try:
        async for message in socket:
            try:
                await handle_message(message.data, process_handler)
            except (BadMessage, InvalidOperation):
                await socket.send_str(
                    create_message('error', {'message': 'Bad message'})
                )
    except asyncio.CancelledError:
        pass
    finally:
        await socket.close()

    print('Closed connection', process_handler.id)
    if process_handler.is_running():
        process_handler.stop()

    return socket
