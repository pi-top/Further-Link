import os
from shutil import copy

from .message import parse_message, BadMessage
from .process_websocket import ProcessWebsocket
from .py_process_handler import PyProcessHandler

WORK_DIR = os.environ.get('FURTHER_LINK_WORK_DIR', '/tmp')
LIB = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(LIB):
    file = os.path.join(LIB, file_name)
    if os.path.isfile(os.path.join(LIB, file)):
        copy(file, WORK_DIR)


class PyWebsocket(ProcessWebsocket):
    async def _handle_message(self, message):
        m_type, m_data = parse_message(message)

        if (m_type == 'start'
                and 'sourceScript' in m_data
                and isinstance(m_data.get('sourceScript'), str)):
            await self.process_handler.start(m_data['sourceScript'])

        elif (m_type == 'stdin'
              and 'input' in m_data
              and isinstance(m_data.get('input'), str)):
            await self.process_handler.send_input(m_data['input'])

        elif m_type == 'stop':
            self.process_handler.stop()

        else:
            raise BadMessage()


async def run_py(request):
    return await PyWebsocket(PyProcessHandler, work_dir=WORK_DIR).handle(request)
