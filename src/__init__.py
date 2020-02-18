import os
import asyncio
from shutil import copy
import websockets

from .message import parse_message, create_message, BadMessage
from .process_handler import ProcessHandler, InvalidOperation

work_dir = os.environ.get("FURTHER_LINK_WORK_DIR", "/tmp")
lib = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(lib):
    file = os.path.join(lib, file_name)
    if os.path.isfile(os.path.join(lib, file)):
        copy(file, work_dir)


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

    elif (m_type == 'stop'):
        process_handler.stop()

    else:
        raise BadMessage()


async def app(socket, path):
    if path != '/exec':
        return

    async def on_start():
        try:
            await socket.send(create_message('started'))
        except websockets.exceptions.ConnectionClosedError:
            pass
        print('Started', process_handler.id)

    async def on_stop(exit_code):
        try:
            await socket.send(create_message('stopped', {'exitCode': exit_code}))
        except websockets.exceptions.ConnectionClosedError:
            pass
        print('Stopped', process_handler.id)

    async def on_output(channel, output):
        try:
            await socket.send(create_message(channel, {'output': output}))
        except websockets.exceptions.ConnectionClosedError:
            pass

    process_handler = ProcessHandler(
        on_start=on_start,
        on_stop=on_stop,
        on_output=on_output,
        work_dir=work_dir
    )
    print('New connection', process_handler.id)

    try:
        async for message in socket:
            try:
                await handle_message(message, process_handler)
            except (BadMessage, InvalidOperation):
                await socket.send(
                    create_message('error', {'message': 'Bad message'})
                )
    except websockets.exceptions.ConnectionClosedError:
        print('Closed connection', id(socket))
    finally:
        if process_handler.is_running():
            process_handler.stop()
