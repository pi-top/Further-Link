import os
import asyncio

from shutil import copy, rmtree
from aiohttp import web, WSMsgType, ClientSession
import aiofiles

from .message import parse_message, create_message, BadMessage, BadUpload
from .process_handler import ProcessHandler, InvalidOperation
from .upload import upload, directory_is_valid

# TODO:- Make lib available for import


async def status(_):
    return web.Response(text='OK')


async def handle_message(message, process_handler, socket):
    m_type, m_data = parse_message(message)

    if (m_type == 'start'
            and 'sourceScript' in m_data
            and isinstance(m_data.get('sourceScript'), str)):
        await process_handler.start(script=m_data['sourceScript'])

    elif (m_type == 'start'
            and 'sourcePath' in m_data
            and isinstance(m_data.get('sourcePath'), str)):
        await process_handler.start(path=m_data['sourcePath'])

    elif (m_type == 'upload'
            and 'directory' in m_data
            and directory_is_valid(m_data.get('directory'))):
        await upload(m_data.get('directory'))
        await socket.send_str(create_message('uploaded'))

    elif (m_type == 'stdin'
          and 'input' in m_data
          and isinstance(m_data.get('input'), str)):
        await process_handler.send_input(m_data['input'])

    elif (m_type == 'ping'):
        await socket.send_str(create_message('pong'))

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

    process_handler = ProcessHandler(
        on_start=on_start,
        on_stop=on_stop,
        on_output=on_output,
    )
    print('New connection', process_handler.id)

    try:
        async for message in socket:
            try:
                await handle_message(message.data, process_handler, socket)

            except BadUpload:
                await socket.send_str(
                    create_message('error', {'message': 'Bad upload'})
                )

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
