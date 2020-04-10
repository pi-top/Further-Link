import asyncio

from aiohttp import web, WSMsgType

from .message import create_message, BadMessage
from .process_handler import ProcessHandler, InvalidOperation


class ProcessWebsocket:
    def __init__(self, HandlerClass=ProcessHandler, **handler_kwargs):
        self.HandlerClass = HandlerClass
        self.handler_kwargs = handler_kwargs
        self.socket = None
        self.process_handler = None

    async def handle(self, request):
        self.socket = web.WebSocketResponse()
        await self.socket.prepare(request)

        async def on_start():
            await self.socket.send_str(create_message('started'))
            print('Started', self.process_handler.id)

        async def on_stop(exit_code):
            await self.socket.send_str(create_message('stopped', {'exitCode': exit_code}))
            print('Stopped', self.process_handler.id)

        async def on_output(channel, output):
            await self.socket.send_str(create_message(channel, {'output': output}))

        self.process_handler = self.HandlerClass(
            on_start=on_start,
            on_stop=on_stop,
            on_output=on_output,
            **self.handler_kwargs
        )
        print('New connection', self.process_handler.id)

        try:
            async for message in self.socket:
                try:
                    await self._handle_message(message.data)
                except (BadMessage, InvalidOperation):
                    await self.socket.send_str(
                        create_message('error', {'message': 'Bad message'})
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await self.socket.close()

        print('Closed connection', self.process_handler.id)
        if self.process_handler.is_running():
            self.process_handler.stop()

        return self.socket

    async def _handle_message(self, message):
        raise BadMessage()
