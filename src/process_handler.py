import asyncio
import pwd
import os
import signal

import aiofiles

IPC_CHANNELS = [
    'video'
]


def get_cmd_prefix():
    # run as pi user if available
    for user in pwd.getpwall():
        if user[0] == 'pi':
            return 'sudo -u pi '
    return ''


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, on_start, on_stop, on_output, on_ping, work_dir='/tmp'):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_output = on_output
        self.work_dir = work_dir
        self.on_ping = on_ping

        self.id = str(id(self))
        self.process = None

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, script):
        if self.is_running() or not isinstance(script, str):
            raise InvalidOperation()

        main_filename = self._get_main_filename()
        async with aiofiles.open(main_filename, 'w+') as file:
            await file.write(script)

        command = get_cmd_prefix() + 'python3 -u ' + main_filename
        self.process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid)  # make a process group for this and children

        asyncio.create_task(self._communicate())

        if self.on_start:
            await self.on_start()

    def is_running(self):
        return hasattr(self, 'process') and self.process is not None
    
    async def ping(self):
        if self.on_ping:
            await self.on_ping()

    def stop(self):
        if not self.is_running():
            raise InvalidOperation()
        # send TERM to process group in case we have child processes
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    async def send_input(self, content):
        if not self.is_running() or not isinstance(content, str):
            raise InvalidOperation()

        self.process.stdin.write(content.encode('utf-8'))
        await self.process.stdin.drain()

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

    async def _handle_output(self, stream_name):
        stream = getattr(self.process, stream_name)
        while True:
            data = await stream.read(4096)
            if data == b'':
                break

            output = data.decode(encoding='utf-8')
            if self.on_output:
                await self.on_output(stream_name, output)

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
