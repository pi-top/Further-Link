import asyncio
import os
import signal

import aiofiles

from .process_handler import ProcessHandler, InvalidOperation

IPC_CHANNELS = [
    'video'
]


class PyProcessHandler(ProcessHandler):
    def __init__(self, *args, work_dir='/tmp', **kwargs):
        self.work_dir = work_dir
        super().__init__(*args, **kwargs)

    async def start(self, script):
        if self.is_running() or not isinstance(script, str):
            raise InvalidOperation()

        main_filename = self._get_main_filename()
        async with aiofiles.open(main_filename, 'w+') as file:
            await file.write(script)

        command = 'python3 -u ' + main_filename
        await super().start(command)

    def _get_main_filename(self):
        return self.work_dir + '/' + self.id + '.py'

    def _get_ipc_filename(self, channel):
        return self.work_dir + '/' + self.id + '.' + channel + '.sock'

    async def _communicate(self):
        output_tasks = [
            asyncio.create_task(self._handle_output('stdout')),
            asyncio.create_task(self._handle_output('stderr')),
        ]

        ipc_tasks = []
        for name in IPC_CHANNELS:
            ipc_tasks.append(asyncio.create_task(
                self._handle_ipc(name)
            ))

        # allow the output tasks to finish & flush
        await asyncio.wait(output_tasks)

        # stop ongoing ipc servers
        for task in ipc_tasks:
            task.cancel()
        await asyncio.wait(ipc_tasks)

        # process should be done now but await it to get exit code
        exit_code = await self.process.wait()
        self.process = None
        await self._clean_up()

        if self.on_stop:
            await self.on_stop(exit_code)

    async def _handle_ipc(self, channel):
        async def handle_connection(reader, _):
            message = ''
            while True:
                data = await reader.read(4096)
                if data == b'':
                    break

                tokens = data.decode('utf-8').strip().split()
                if tokens[0] == channel:
                    if len(message) > 0:
                        if self.on_output:
                            await self.on_output(channel, message)
                        message = ''
                    message += tokens[1]
                else:
                    message += tokens[0]

        ipc_filename = self._get_ipc_filename(channel)
        await asyncio.start_unix_server(handle_connection, path=ipc_filename)

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
