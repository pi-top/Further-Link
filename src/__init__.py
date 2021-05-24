import asyncio
import json
import logging

from aiohttp import web

from .ssl_context import ssl_context  # noqa: F401
from .apt_version import apt_version  # noqa: F401
from .message import parse_message, create_message, BadMessage
from .process_handler import ProcessHandler, InvalidOperation
from .upload import upload, directory_is_valid, BadUpload
from .lib.further_link import (  # noqa: F401
    __version__,
    start_ipc_server,
    async_start_ipc_server,
    ipc_send,
    async_ipc_send,
    ipc_cleanup
)


async def status(_):
    return web.Response(text='OK')


async def version(_):
    return web.Response(text=json.dumps({'version': __version__}))


async def handle_message(message, process_handler, socket):
    m_type, m_data = parse_message(message)

    if (
        m_type == 'start'
        and 'sourceScript' in m_data
        and isinstance(m_data.get('sourceScript'), str)
    ):
        path = m_data.get('directoryName') if (
            'directoryName' in m_data
            and isinstance(m_data.get('directoryName'), str)
            and len(m_data.get('directoryName')) > 0
        ) else None
        await process_handler.start(
            script=m_data['sourceScript'],
            path=path,
        )

    elif (m_type == 'start'
            and 'sourcePath' in m_data
            and isinstance(m_data.get('sourcePath'), str)
            and len(m_data.get('sourcePath')) > 0
          ):
        await process_handler.start(path=m_data['sourcePath'])

    elif (m_type == 'upload'
            and 'directory' in m_data
            and directory_is_valid(m_data.get('directory'))):
        await upload(m_data.get('directory'), process_handler.work_dir)
        await socket.send_str(create_message('uploaded'))

    elif (m_type == 'stdin'
          and 'input' in m_data
          and isinstance(m_data.get('input'), str)):
        await process_handler.send_input(m_data['input'])

    elif (m_type == 'ping'):
        await socket.send_str(create_message('pong'))

    elif m_type == 'stop':
        process_handler.stop()

    elif (m_type == 'keyevent'
          and 'key' in m_data
          and isinstance(m_data.get('key'), str)
          and 'event' in m_data
          and isinstance(m_data.get('event'), str)):
        await process_handler.send_key_event(m_data['key'], m_data['event'])

    else:
        raise BadMessage()


async def run_py(request):
    query_params = request.query
    user = query_params.get('user', None)
    pty = query_params.get('pty', '').lower() in ['1', 'true']

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    async def on_start():
        await socket.send_str(create_message('started'))
        logging.info(f'{process_handler.id} Started')

    async def on_stop(exit_code):
        try:
            await socket.send_str(
                create_message('stopped', {'exitCode': exit_code})
            )
        except ConnectionResetError:
            pass  # already disconnected
        logging.info(f'{process_handler.id} Stopped')

    async def on_output(channel, output):
        logging.debug(
            f'{process_handler.id} Sending Output {channel} {output}'
        )
        await socket.send_str(create_message(channel, {'output': output}))

    process_handler = ProcessHandler(user=user, pty=pty)
    process_handler.on_start = on_start
    process_handler.on_stop = on_stop
    process_handler.on_output = on_output
    logging.info(f'{process_handler.id} New connection')

    try:
        async for message in socket:
            logging.debug(
                f'{process_handler.id} Received Message {message.data}'
            )
            try:
                await handle_message(message.data, process_handler, socket)

            except BadUpload:
                logging.exception(f'{process_handler.id} Bad Upload')
                await socket.send_str(
                    create_message('error', {'message': 'Bad upload'})
                )

            except (BadMessage, InvalidOperation):
                logging.exception(f'{process_handler.id} Bad Message')
                await socket.send_str(
                    create_message('error', {'message': 'Bad message'})
                )

            except Exception:
                logging.exception(f'{process_handler.id} Message Exception')
                await socket.send_str(
                    create_message('error', {'message': 'Message Exception'})
                )

    except asyncio.CancelledError:
        pass
    finally:
        await socket.close()

    logging.info(f'{process_handler.id} Closed connection')
    if process_handler.is_running():
        process_handler.stop()

    return socket
