import asyncio
import os
import signal

import aiofiles

from .user_config import get_current_user, get_run_as_user_prefix

IPC_CHANNELS = [
    'video'
]


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, user=None):
        self.user = 'pi' if user is None else user
        self.temp_dir = os.environ.get('FURTHER_LINK_TEMP_DIR', '/tmp')
        self.work_dir = os.environ.get(
            'FURTHER_LINK_WORK_DIR', os.path.join(os.environ.get('HOME'), 'further'))

        self.id = str(id(self))
        self.process = None

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, script=None, path=None):
        if self.is_running():
            raise InvalidOperation()

        entrypoint = await self._get_entrypoint(script, path)

        asyncio.create_task(self._ipc_communicate())

        command = 'python3 -u ' + entrypoint
        if self.user != get_current_user():
            command_prefix = get_run_as_user_prefix(self.user)
            if command_prefix is not None:
                command = get_run_as_user_prefix(self.user) + command

        self.process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid)  # make a process group for this and children

        asyncio.create_task(self._process_communicate())

        if self.on_start:
            await self.on_start()

    def is_running(self):
        return hasattr(self, 'process') and self.process is not None

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

    async def _get_entrypoint(self, script, path):
        # find/create path dir and write script to file
        if isinstance(path, str) and isinstance(script, str):
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            entrypoint = self._get_script_filename(path)

            async with aiofiles.open(entrypoint, 'w+') as file:
                await file.write(script)

        # old style, no directory path but create script
        elif path is None and isinstance(script, str):
            entrypoint = self._get_script_filename()

            async with aiofiles.open(entrypoint, 'w+') as file:
                await file.write(script)

        # no script provided, entrypoint is path, may be relative to work_dir
        elif script is None and isinstance(path, str):
            first_char = path[0]
            if first_char == '/':
                entrypoint = path
            else:
                entrypoint = "{}/{}".format(self.work_dir, path)

        else:
            raise InvalidOperation()

        return entrypoint

    def _get_script_filename(self, path=None):
        dir = path if isinstance(path, str) else self.temp_dir
        return dir + '/' + self.id + '.py'

    def _get_ipc_filename(self, channel):
        return self.temp_dir + '/' + self.id + '.' + channel + '.sock'

    async def _ipc_communicate(self):
        self.ipc_tasks = []
        for name in IPC_CHANNELS:
            self.ipc_tasks.append(asyncio.create_task(
                self._handle_ipc(name)
            ))

    async def _process_communicate(self):
        output_tasks = [
            asyncio.create_task(self._handle_output('stdout')),
            asyncio.create_task(self._handle_output('stderr')),
        ]

        # allow the output tasks to finish & flush
        await asyncio.wait(output_tasks)

        # stop ongoing ipc servers
        for task in self.ipc_tasks:
            task.cancel()
        await asyncio.wait(self.ipc_tasks)

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
                    message += ' '.join(tokens[1:])
                else:
                    message += ' '.join(tokens[1:])

        ipc_filename = self._get_ipc_filename(channel)
        await asyncio.start_unix_server(handle_connection, path=ipc_filename)
        os.chmod(ipc_filename, 0o666)  # ensure pi user can use this too

    async def _clean_up(self):
        # aiofiles.os.remove not released to debian buster
        # os.remove should not block significantly, just fires a single syscall
        try:
            os.remove(self._get_main_filename())
            for name in IPC_CHANNELS:
                try:
                    os.remove(self._get_ipc_filename(name))
                except:
                    pass
        except:
            pass
