import asyncio
import json

from aiohttp import web

from .lib.further_link import __version__
from .apt_version import apt_version  # noqa: F401
from .message import parse_message, create_message, BadMessage
from .process_handler import ProcessHandler, InvalidOperation
from .upload import upload, directory_is_valid, BadUpload


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

    else:
        raise BadMessage()


async def run_py(request):
    query_params = request.query
    user = query_params.get('user', None)

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    async def on_start():
        await socket.send_str(create_message('started'))
        print('Started', process_handler.id)

    async def on_stop(exit_code):
        await socket.send_str(
            create_message('stopped', {'exitCode': exit_code})
        )
        print('Stopped', process_handler.id)

    async def on_output(channel, output):
        await socket.send_str(create_message(channel, {'output': output}))

    process_handler = ProcessHandler(user=user)
    process_handler.on_start = on_start
    process_handler.on_stop = on_stop
    process_handler.on_output = on_output
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
