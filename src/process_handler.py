import asyncio
from threading import Thread
import os
from time import sleep
from functools import partial
import socket
import aiofiles

from .message import create_message

ipc_channel_names = [
    # 'video'
]


class ProcessHandler:
    def __init__(self, websocket, work_dir="/tmp"):
        self.websocket = websocket
        self.work_dir = work_dir
        self.id = str(id(self.websocket))

    def __del__(self):
        self.stop()

    async def start(self, script):
        print('Starting', self.id)

        main_filename = self._get_main_filename()
        async with aiofiles.open(main_filename, 'w+') as f:
            await f.write(script)

        command = 'python3 -u ' + main_filename
        self.process = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        self.websocket.send(create_message('started'))

        # self.ipc_channels = {}
        # for name in ipc_channel_names:
        #     ipc_filename = self._get_ipc_filename(name)
        #     if os.path.exists(ipc_filename):
        #         os.remove(ipc_filename)
        #     self.ipc_channels[name] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        #     self.ipc_channels[name].bind(ipc_filename)
        #     self.ipc_channels[name].setblocking(0)

        #     handle_ipc = partial(self.handle_ipc, channel=name)
        #     Thread(target=handle_ipc, daemon=True).start()

        await asyncio.wait([
            self._handle_output('stdout'),
            self._handle_output('stderr')
        ])

        exitCode = await self.process.wait()
        self.process = None

        self.websocket.send(create_message('stopped', {
            'exitCode': exitCode
        }))
        await self._clean_up()
        print('Stopped', self.id)

    def send_input(self, content):
        print(content)
        self.process.stdin.write(content.encode('utf-8'))
        self.process.stdin.flush()

    def stop(self):
        if self.is_running():
            self.process.terminate()

    def is_running(self):
        return hasattr(self, 'process') and self.process is not None

    async def _clean_up(self):
        try:
            await aiofiles.os.remove(self._get_main_filename())
            for name in ipc_channel_names:
                try:
                    await aiofiles.os.remove(self._get_ipc_filename(name))
                except:
                    pass
        except:
            pass

    def _get_main_filename(self):
        return self.work_dir + '/' + self.id + '.py'

    def _get_ipc_filename(self, channel):
        return self.work_dir + '/' + self.id + '.' + channel + '.sock'

    async def _handle_output(self, stream_name):
        stream = getattr(self.process, stream_name)
        while True:
            line = await stream.readline()
            output = line.decode(encoding='utf-8')
            if line:
                self.websocket.send(create_message(stream_name, {
                    'output': output
                }))
            else:
                break

    # def handle_ipc(self, channel):
    #     self.ipc_channels[channel].listen(1)
    #     while True:
    #         if not self.is_running():
    #             break
    #         try:
    #             conn, addr = self.ipc_channels[channel].accept()
    #             message = ''
    #             while True:
    #                 if not self.is_running():
    #                     break
    #                 try:
    #                     data = conn.recv(4096)
    #                     if data:
    #                         tokens = data.decode("utf-8").strip().split()
    #                         if tokens[0] == channel:
    #                             if len(message) > 0:
    #                                 self.websocket.send(create_message(channel, {
    #                                     'message': message
    #                                 }))
    #                                 message = ''
    #                             message += tokens[1]
    #                         else:
    #                             message += tokens[0]
    #                 except:
    #                     sleep(0.001)
    #                     continue
    #             conn.close()
    #         except:
    #             sleep(0.1)
    #             continue
