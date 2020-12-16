import asyncio
import os
import signal
import pty
import pathlib

import aiofiles

from .user_config import default_user, get_current_user, user_exists, \
    get_working_directory, get_temp_dir

IPC_CHANNELS = [
    'video'
]

dirname = pathlib.Path(__file__).parent.absolute()
further_link_module_path = os.path.join(dirname, 'lib')


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, user=None, pty=False):
        self.user = default_user() if user is None else user
        self.pty = pty
        self.work_dir = get_working_directory(user)
        self.temp_dir = get_temp_dir()

        self.id = str(id(self))
        self.process = None

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, script=None, path=None):
        if self.is_running():
            raise InvalidOperation()

        entrypoint = await self._get_entrypoint(script, path)
        self._remove_entrypoint = entrypoint if script is not None else None

        asyncio.create_task(self._ipc_communicate())

        stdio = asyncio.subprocess.PIPE

        if self.pty:
            # communicate through a pty for terminal 'cooked mode' behaviour
            master, slave = pty.openpty()
            self.pty_master = await aiofiles.open(master, 'w+b', 0)
            self.pty_slave = await aiofiles.open(slave, 'r+b', 0)

            stdio = self.pty_slave

        command = 'python3 -u ' + entrypoint
        if self.user != get_current_user() and user_exists(self.user):
            command = f'sudo -u {self.user} --preserve-env=PYTHONPATH {command}'

        process_env = os.environ.copy()
        process_env["PYTHONPATH"] = further_link_module_path

        self.process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdin=stdio,
            stdout=stdio,
            stderr=stdio,
            env=process_env,
            cwd=os.path.dirname(entrypoint),
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
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    async def send_input(self, content):
        if not self.is_running() or not isinstance(content, str):
            raise InvalidOperation()

        content_bytes = content.encode('utf-8')

        if self.pty:
            await self.pty_master.write(content_bytes)
        else:
            self.process.stdin.write(content_bytes)
            await self.process.stdin.drain()

    async def _get_entrypoint(self, script=None, path=None):
        if isinstance(path, str):
            # path is absolute or relative to work_dir
            first_char = path[0]
            if first_char != '/':
                path = os.path.join(self.work_dir, path)

            path_dirs = path if isinstance(
                script, str) else os.path.dirname(path)

            # if there's a script to create, create path dirs for it to go in
            if not os.path.exists(path_dirs) and isinstance(script, str):
                os.makedirs(path_dirs, exist_ok=True)

        if isinstance(script, str):
            # write script to file, at path if given, otherwise temp
            entrypoint = self._get_script_filename(path)
            async with aiofiles.open(entrypoint, 'w+') as file:
                await file.write(script)

            return entrypoint

        if path is not None:
            return path

        raise InvalidOperation()

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
        output_tasks = []
        if self.pty:
            output_tasks.append(asyncio.create_task(
                self._handle_output(self.pty_master, 'stdout')
            ))
        else:
            output_tasks.append(asyncio.create_task(
                self._handle_output(self.process.stdout, 'stdout')
            ))
            output_tasks.append(asyncio.create_task(
                self._handle_output(self.process.stderr, 'stderr')
            ))

        # wait for process to exit
        exit_code = await self.process.wait()

        # stop ongoing io tasks
        for task in output_tasks:
            task.cancel()
        await asyncio.wait(output_tasks)

        for task in self.ipc_tasks:
            task.cancel()
        await asyncio.wait(self.ipc_tasks)

        await self._clean_up()
        self.process = None

        if self.on_stop:
            await self.on_stop(exit_code)

    async def _handle_output(self, stream, channel):
        while True:
            data = await stream.read(4096)
            if data == b'':
                break

            output = data.decode(encoding='utf-8')
            if self.on_output:
                await self.on_output(channel, output)

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
                    message += ' '.join(tokens)

        ipc_filename = self._get_ipc_filename(channel)
        await asyncio.start_unix_server(handle_connection, path=ipc_filename)
        os.chmod(ipc_filename, 0o666)  # ensure pi user can use this too

    async def _clean_up(self):
        # aiofiles.os.remove not released to debian buster
        # os.remove should not block significantly, just fires a single syscall
        try:
            if self._remove_entrypoint is not None:
                os.remove(self._remove_entrypoint)
        except Exception:
            pass

        try:
            if self.pty:
                self.pty_master.close()
                self.pty_slave.close()
                os.remove(self.pty_master)
                os.remove(self.pty_slave)
        except Exception:
            pass

        for name in IPC_CHANNELS:
            try:
                os.remove(self._get_ipc_filename(name))
            except Exception:
                pass
