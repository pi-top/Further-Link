import asyncio
import logging
import os
import signal
from functools import partial
from shlex import split

from pt_web_vnc.vnc import async_start, async_stop

from ..util.async_helpers import ringbuf_read, timeout
from ..util.id_generator import IdGenerator
from ..util.ipc import async_ipc_send, async_start_ipc_server, ipc_cleanup
from ..util.pty import Pty
from ..util.sdk import get_first_display
from ..util.user_config import (
    get_current_user,
    get_gid,
    get_grp_ids,
    get_home_directory,
    get_shell,
    get_uid,
    get_working_directory,
    get_xdg_runtime_dir,
    user_exists,
)
from ..util.vnc import VNC_CERTIFICATE_PATH

SERVER_IPC_CHANNELS = [
    "video",
    "keylisten",
]


class InvalidOperation(Exception):
    pass


# each run will need a unique id
# one use of the id is for the pt-web-vnc virtual display id and port numbers
# so we must use +ve int < 1000, with 0-99 reserved for other uses
# envvar FURTHER_LINK_MAX_PROCESSES can be used to limit the range
var_max_processes = os.environ.get("FURTHER_LINK_MAX_PROCESSES")
MAX = 900
if isinstance(var_max_processes, str) and var_max_processes.isdigit():
    max_processes = int(var_max_processes)
else:
    max_processes = MAX
if 1 > max_processes > MAX:
    max_processes = MAX

id_generator = IdGenerator(min_value=100, max_value=99 + max_processes)


class ProcessHandler:
    def __init__(self, user, pty=False):
        self.use_pty = pty
        self.id = id_generator.create()
        assert user_exists(user)
        self.user = user
        self.on_display_activity = None

    async def start(self, *args, **kwargs):
        try:
            await self._start(*args, **kwargs)
        except Exception as e:
            logging.exception(f"{self.id} Start error: {e}")
            await self._clean_up()

    async def _start(self, command, work_dir=None, env={}, novncOptions={}):
        self.work_dir = work_dir or get_working_directory(self.user)
        self.novnc = novncOptions.get("enabled", False)

        stdio = asyncio.subprocess.PIPE

        if self.use_pty:
            logging.debug(f"{self.id} Starting PTY")
            # communicate through a pty for terminal 'cooked mode' behaviour
            self.pty = await Pty.create(self.user)

            # set terminal size to a minimum that we display in Further
            self.pty.set_winsize(4, 60)

            stdio = self.pty.back

            logging.debug(f"{self.id} Setup pty")

        process_env = {**os.environ.copy(), **env}
        process_env["TERM"] = "xterm-256color"  # perhaps should be param

        if self.user:
            process_env["USER"] = self.user
            process_env["LOGNAME"] = self.user
            process_env["HOME"] = get_home_directory(self.user)
            process_env["XDG_RUNTIME_DIR"] = get_xdg_runtime_dir(self.user)
            process_env["SHELL"] = get_shell(self.user)
            process_env["PWD"] = self.work_dir
            # remove None values
            process_env = {k: v for k, v in process_env.items() if v is not None}

        # set $DISPLAY so that user can open GUI windows
        if self.novnc:
            logging.debug(f"{self.id} Starting NOVNC")
            process_env["DISPLAY"] = f":{self.id}"
            await async_start(
                display_id=self.id,
                on_display_activity=self.on_display_activity,
                ssl_certificate=VNC_CERTIFICATE_PATH,
                with_window_manager=True,
                height=novncOptions.get("height"),
                width=novncOptions.get("width"),
            )
            logging.debug(f"{self.id} Setup novnc")
        else:
            default_display = get_first_display()
            if default_display:
                process_env["DISPLAY"] = default_display

        def preexec():
            if self.user != get_current_user():
                # set the process group id for user
                os.setgid(get_gid(self.user))

                # set the process supplemental groups for user
                os.setgroups(get_grp_ids(self.user))

                # set the process user id
                # must do this after setting groups as it reduces privilege
                os.setuid(get_uid(self.user))

            # create a new session and process group for the user process and
            # subprocesses. this allows us to clean them up in one go as well
            # as allowing a shell process to be a 'controlling terminal'
            os.setsid()

        logging.debug(f"{self.id} Starting process")
        self.process = await asyncio.create_subprocess_exec(
            *split(command),
            stdin=stdio,
            stdout=stdio,
            stderr=stdio,
            env=process_env,
            cwd=self.work_dir,
            preexec_fn=preexec,
        )
        logging.debug(f"{self.id} Started process")

        if self.on_start:
            await self.on_start()

        asyncio.create_task(self._process_communicate())  # asap
        try:
            self.pgid = os.getpgid(self.process.pid)  # retain for cleanup
            asyncio.create_task(self._ipc_communicate())  # after as uses pgid
        except ProcessLookupError:
            logging.debug(f"{self.id} Process lookup failed - running without IPC")
            # the process is done faster than we can look up gpid!
            self.pgid = None

        logging.debug(f"{self.id} Start complete")

    def is_running(self):
        return hasattr(self, "process") and self.process is not None

    async def stop(self):
        if not self.is_running():
            raise InvalidOperation()
        # send signal to process group in case we have child processes
        try:
            logging.debug(f"{self.id} Stopping with SIGTERM")
            os.killpg(self.pgid, signal.SIGTERM)
            stopped = asyncio.create_task(self.process.wait())
            done = await timeout(stopped, 0.1)

            # if SIGTERM didn't stop the process already, send SIGKILL
            if stopped not in done:
                logging.debug(f"{self.id} Stopping with SIGKILL")
                os.killpg(self.pgid, signal.SIGKILL)

            logging.debug(f"{self.id} Stop complete")
        except ProcessLookupError:
            logging.debug(f"{self.id} Could not stop - ProcessLookupError")

    async def send_input(self, content):
        if not self.is_running() or not isinstance(content, str):
            logging.debug(f"{self.id} Not receiving input as not running")
            raise InvalidOperation()

        content_bytes = content.encode("utf-8")

        if self.use_pty:
            # if fstat errors file is already closed and writing will hang
            try:
                os.fstat(self.pty.front.fileno())
                await self.pty.front.write(content_bytes)
            except OSError:
                logging.debug(f"{self.id} Not receiving input as pty closed")
        else:
            self.process.stdin.write(content_bytes)
            await self.process.stdin.drain()

    async def resize_pty(self, rows, cols):
        if not self.is_running() or not self.use_pty:
            raise InvalidOperation()

        self.pty.set_winsize(rows, cols)

    async def send_key_event(self, key, event):
        if (
            not self.is_running()
            or not isinstance(key, str)
            or not isinstance(event, str)
        ):
            raise InvalidOperation()

        content_bytes = f"{key} {event}".encode("utf-8")
        await async_ipc_send("keyevent", content_bytes, pgid=self.pgid)

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
        if self.use_pty:
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.pty.front, "stdout"))
            )
        else:
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.process.stdout, "stdout"))
            )
            output_tasks.append(
                asyncio.create_task(self._handle_output(self.process.stderr, "stderr"))
            )

        logging.debug(f"{self.id} Monitoring output")

        # wait for process to exit
        await self.process.wait()

        logging.debug(f"{self.id} Process exited")

        # wait a little for the io tasks to complete to let them send
        # output produced right before the process stopped
        # but cancel them after a timeout if they don't stop themselves
        await timeout(output_tasks, 1)
        if hasattr(self, "ipc_tasks"):
            await timeout(self.ipc_tasks, 0.1)

        await self._handle_process_end()

    async def _handle_process_end(self):
        exit_code = await self.process.wait()

        if self.process:
            await self._clean_up()

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
        logging.debug(f"{self.id} Starting cleanup")
        if getattr(self, "pty", None):
            logging.debug(f"{self.id} Cleaning up PTY")
            await self.pty.clean_up()
            self.pty = None

        if getattr(self, "novnc", None):
            logging.debug(f"{self.id} Cleaning up NOVNC")
            try:
                await async_stop(self.id)
            except Exception as e:
                logging.exception(f"{self.id} NOVNC Cleanup error: {e}")

        if getattr(self, "ipc_tasks", None):
            logging.debug(f"{self.id} Cleaning up IPC")
            try:
                for channel in SERVER_IPC_CHANNELS:
                    ipc_cleanup(channel, pgid=self.pgid)
                ipc_servers = await asyncio.gather(*self.ipc_tasks)
                for server in ipc_servers:
                    server.close()
            except Exception as e:
                logging.exception(f"{self.id} IPC Cleanup error: {e}")

        logging.debug(f"{self.id} Releasing ID")
        id_generator.free(self.id)

        self.process = None
        logging.debug(f"{self.id} Cleanup complete")
