import asyncio
import os
import signal
from pty import openpty
from functools import partial
import aiofiles
from pitopcommon.current_session_info import get_first_display

from .lib.further_link import (
    async_start_ipc_server,
    async_ipc_send,
    ipc_cleanup
)
from .util.async_helpers import ringbuf_read, timeout
from .util.user_config import get_current_user, user_exists, \
    get_working_directory
from .util.terminal import set_winsize

SERVER_IPC_CHANNELS = [
    'video',
    'keylisten',
]


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, user=None, pty=False):
        self.user = user
        self.pty = pty

        self.id = str(id(self))
        self.process = None
        self.pgid = None

    async def start(self, command, work_dir=None, env={}):
        self.work_dir = work_dir or get_working_directory(self.user)

        stdio = asyncio.subprocess.PIPE

        if self.pty:
            # communicate through a pty for terminal 'cooked mode' behaviour
            master, slave = openpty()
            self.pty_master = await aiofiles.open(master, 'w+b', 0)
            self.pty_slave = await aiofiles.open(slave, 'r+b', 0)

            # set terminal size to a minimum that we display in Further
            set_winsize(slave, 4, 60)
            # TODO size should be updated by a resize message

            stdio = self.pty_slave

        if self.user != get_current_user() and user_exists(self.user):
            # run command as user but preserving provided environment
            command = f'sudo --preserve-env -u {self.user} {command}'

        process_env = {**os.environ.copy(), **env}

        # Ensure that DISPLAY is set, so that user can open GUI windows
        display = get_first_display()
        if display is not None:
            process_env["DISPLAY"] = display

        self.process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdin=stdio,
            stdout=stdio,
            stderr=stdio,
            env=process_env,
            cwd=self.work_dir,
            preexec_fn=os.setsid)  # make a process group for this and children

        self.pgid = os.getpgid(self.process.pid)  # retain for cleanup

        asyncio.create_task(self._ipc_communicate())  # after exec as uses pgid
        asyncio.create_task(self._process_communicate())

        if self.on_start:
            await self.on_start()

    def is_running(self):
        return hasattr(self, 'process') and self.process is not None

    async def stop(self):
        if not self.is_running():
            raise InvalidOperation()
        # send signal to process group in case we have child processes
        try:
            os.killpg(self.pgid, signal.SIGTERM)
            stopped = asyncio.create_task(self.process.wait())
            done = await timeout(stopped, 0.1)

            # if SIGTERM didn't stop the process already, send SIGKILL
            if stopped not in done:
                os.killpg(self.pgid, signal.SIGKILL)
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

    async def send_key_event(self, key, event):
        if (
            not self.is_running()
            or not isinstance(key, str)
            or not isinstance(event, str)
        ):
            raise InvalidOperation()

        content_bytes = f'{key} {event}'.encode('utf-8')
        await async_ipc_send('keyevent', content_bytes, pgid=self.pgid)

    async def _ipc_communicate(self):
        self.ipc_tasks = []
        for channel in SERVER_IPC_CHANNELS:
            self.ipc_tasks.append(asyncio.create_task(
                async_start_ipc_server(channel,
                                       partial(self.on_output, channel),
                                       pgid=self.pgid)
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
        await asyncio.sleep(0.1)
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
        await ringbuf_read(
            stream,
            output_callback=partial(self.on_output, channel),
            buffer_time=0.1,
            max_chunks=50,
            chunk_size=256,
            done_condition=self.process.wait
        )

    async def _clean_up(self):
        try:
            if self.pty:
                self.pty_master.close()
                self.pty_slave.close()
                os.remove(self.pty_master)
                os.remove(self.pty_slave)
        except Exception:
            pass

        for channel in SERVER_IPC_CHANNELS:
            ipc_cleanup(channel, pgid=self.pgid)
