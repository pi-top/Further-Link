import asyncio
import logging

from aiohttp import web

from .message import parse_message, create_message, BadMessage
from .process_handler import InvalidOperation
from .py_process_handler import PyProcessHandler
from .shell_process_handler import ShellProcessHandler
from .user_config import default_user


class RunManager:
    def __init__(self, socket, user=None, pty=False):
        self.socket = socket
        self.user = default_user() if user is None else user
        self.pty = pty

        self.id = str(id(self))
        self.process_handlers = {}

    def __del__(self):
        self.stop()

    def stop(self):
        for p in self.process_handlers.values():
            try:
                p.stop()
            except InvalidOperation:
                pass

    async def handle_message(self, message):
        try:
            m_type, m_data, m_process = parse_message(message)

            process_handler = self.process_handlers.get(m_process)

            if m_type == 'ping':
                await self.socket.send_str(create_message('pong'))

            elif m_type == 'start' and not process_handler and m_process:
                await self.add_handler(m_process, m_data.get('runner'), m_data)

            elif (m_type == 'stdin'
                  and process_handler
                  and 'input' in m_data
                  and isinstance(m_data.get('input'), str)):
                await process_handler.send_input(m_data['input'])

            elif m_type == 'stop' and process_handler:
                process_handler.stop()

            elif (m_type == 'keyevent'
                  and process_handler
                  and 'key' in m_data
                  and isinstance(m_data.get('key'), str)
                  and 'event' in m_data
                  and isinstance(m_data.get('event'), str)):
                await process_handler.send_key_event(m_data['key'],
                                                     m_data['event'])

            else:
                raise BadMessage()

        except (BadMessage, InvalidOperation):
            logging.exception(f'{self.id} Bad Message')
            await self.socket.send_str(
                create_message('error', {'message': 'Bad message'})
            )

        except Exception:
            logging.exception(f'{self.id} Message Exception')
            await self.socket.send_str(
                create_message('error', {'message': 'Message Exception'})
            )

    async def add_handler(self, process_id, runner, m_data):
        handler = None

        async def on_start():
            await self.socket.send_str(create_message('started', None,
                                                      process_id))
            logging.info(f'{self.id} Started {process_id}')

        async def on_stop(exit_code):
            try:
                await self.socket.send_str(
                    create_message('stopped', {'exitCode': exit_code},
                                   process_id)
                )
            except ConnectionResetError:
                pass  # already disconnected
            logging.info(f'{self.id} Stopped {process_id}')

        async def on_output(channel, output):
            logging.debug(
                f'{self.id} Sending Output {process_id} {channel} {output}'
            )
            await self.socket.send_str(create_message(channel,
                                                      {'output': output},
                                                      process_id))

        if (
            runner == 'python3'
            and 'sourceScript' in m_data
            and isinstance(m_data.get('sourceScript'), str)
        ):
            path = m_data.get('directoryName') if (
                'directoryName' in m_data
                and isinstance(m_data.get('directoryName'), str)
                and len(m_data.get('directoryName')) > 0
            ) else None

            handler = PyProcessHandler(self.user, self.pty)
            handler.on_start = on_start
            handler.on_stop = on_stop
            handler.on_output = on_output
            await handler.start(script=m_data['sourceScript'], path=path)

        elif (
            runner == 'python3'
            and 'sourcePath' in m_data
            and isinstance(m_data.get('sourcePath'), str)
            and len(m_data.get('sourcePath')) > 0
        ):
            handler = PyProcessHandler(self.user, self.pty)
            handler.on_start = on_start
            handler.on_stop = on_stop
            handler.on_output = on_output
            await handler.start(path=m_data['sourcePath'])

        else:
            raise BadMessage('Start command runner invalid')

        self.process_handlers[id] = handler


async def run(request):
    query_params = request.query
    user = query_params.get('user', None)
    pty = query_params.get('pty', '').lower() in ['1', 'true']

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    run_manager = RunManager(socket, user=user, pty=pty)
    logging.info(f'{run_manager.id} New connection')

    try:
        async for message in socket:
            logging.debug(f'{run_manager.id} Received Message {message.data}')
            await run_manager.handle_message(message.data)

    except asyncio.CancelledError:
        pass

    finally:
        await socket.close()
        logging.info(f'{run_manager.id} Closed connection')
        run_manager.stop()
