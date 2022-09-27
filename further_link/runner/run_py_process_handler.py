import asyncio
import os
import pathlib
import pty
import signal
from functools import partial

import aiofiles

from ..util.async_helpers import ringbuf_read
from ..util.ipc import async_ipc_send, async_start_ipc_server, ipc_cleanup
from ..util.sdk import get_first_display
from ..util.upload import create_directory
from ..util.user_config import (
    default_user,
    get_current_user,
    get_temp_dir,
    get_working_directory,
    user_exists,
)

SERVER_IPC_CHANNELS = [
    "video",
    "keylisten",
]

dirname = pathlib.Path(__file__).parent.absolute()


class InvalidOperation(Exception):
    pass


class RunPyProcessHandler:
    def __init__(self, user=None, pty=False):
        self.user = default_user() if user is None else user
        self.pty = pty
        self.work_dir = get_working_directory(user)
        self.temp_dir = get_temp_dir()

        self.id = str(id(self))
        self.process = None
        self.pgid = None

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, script=None, path=None):
        if self.is_running():
            raise InvalidOperation()

        entrypoint = await self._get_entrypoint(script, path)
        self._remove_entrypoint = entrypoint if script is not None else None

        stdio = asyncio.subprocess.PIPE

        if self.pty:
            # communicate through a pty for terminal 'cooked mode' behaviour
            master, slave = pty.openpty()
            self.pty_master = await aiofiles.open(master, "w+b", 0)
            self.pty_slave = await aiofiles.open(slave, "r+b", 0)

            stdio = self.pty_slave

        cmd = "python3 -u " + entrypoint
        if self.user != get_current_user() and user_exists(self.user):
            cmd = f"sudo -u {self.user} {cmd}"

        process_env = os.environ.copy()

        # Ensure that DISPLAY is set, so that user can open GUI windows
        display = get_first_display()
        if display is not None:
            process_env["DISPLAY"] = display

        self.process = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdin=stdio,
            stdout=stdio,
            stderr=stdio,
            env=process_env,
            cwd=os.path.dirname(entrypoint),
            preexec_fn=os.setsid,
        )  # make a process group for this and children

        self.pgid = os.getpgid(self.process.pid)  # retain for cleanup

        asyncio.create_task(self._ipc_communicate())  # after exec as uses pgid
        asyncio.create_task(self._process_communicate())

        if self.on_start:
            await self.on_start()

    def is_running(self):
        return hasattr(self, "process") and self.process is not None

    def stop(self):
        if not self.is_running():
            raise InvalidOperation()
        # send TERM to process group in case we have child processes
        try:
            os.killpg(self.pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    async def send_input(self, content):
        if not self.is_running() or not isinstance(content, str):
            raise InvalidOperation()

        content_bytes = content.encode("utf-8")

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

        content_bytes = f"{key} {event}".encode("utf-8")
        await async_ipc_send("keyevent", content_bytes, pgid=self.pgid)

    async def _get_entrypoint(self, script=None, path=None):
        if isinstance(path, str):
            # path is absolute or relative to work_dir
            first_char = path[0]
            if first_char != "/":
                path = os.path.join(self.work_dir, path)

            path_dirs = path if isinstance(script, str) else os.path.dirname(path)

            # if there's a script to create, create path dirs for it to go in
            if not os.path.exists(path_dirs) and isinstance(script, str):
                create_directory(path_dirs, self.user)

        if isinstance(script, str):
            # write script to file, at path if given, otherwise temp
            entrypoint = self._get_script_filename(path)
            async with aiofiles.open(entrypoint, "w+") as file:
                await file.write(script)

            return entrypoint

        if path is not None:
            return path

        raise InvalidOperation()

    def _get_script_filename(self, path=None):
        dir = path if isinstance(path, str) else self.temp_dir
        return dir + "/" + self.id + ".py"

    async def _ipc_communicate(self):
        self.ipc_tasks = []
        for channel in SERVER_IPC_CHANNELS:
            self.ipc_tasks.append(
                asyncio.create_task(
                    async_start_ipc_server(
                        channel, partial(self.on_output, channel), pgid=self.pgid
                    )
                )
            )

    async def _process_communicate(self):
        output_tasks = []
        if self.pty:
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.pty_master, "stdout"))
            )
        else:
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.process.stdout, "stdout"))
            )
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.process.stderr, "stderr"))
            )

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
            done_condition=self.process.wait,
        )

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

        for channel in SERVER_IPC_CHANNELS:
            ipc_cleanup(channel, pgid=self.pgid)
