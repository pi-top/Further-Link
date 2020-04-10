from .message import parse_message, BadMessage
from .process_websocket import ProcessWebsocket


class ShellWebsocket(ProcessWebsocket):
    async def _handle_message(self, message):
        m_type, m_data = parse_message(message)

        if m_type == 'start':
            # TODO commands may be run with sudo -u pi, but this env var will
            # be evaulated before switching user, so the shell of the server
            # user may be used rather than pi. need to work out how to get it
            # evaluated as pi
            await self.process_handler.start('$SHELL')

        elif (m_type == 'stdin'
              and 'input' in m_data
              and isinstance(m_data.get('input'), str)):
            await self.process_handler.send_input(m_data['input'])

        elif m_type == 'stop':
            self.process_handler.stop()

        else:
            raise BadMessage()


async def shell(request):
    return await ShellWebsocket().handle(request)
