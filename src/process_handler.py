import asyncio
import os
import pwd
import signal
from shlex import split


def get_cmd_prefix():
    # run as pi user if available
    for user in pwd.getpwall():
        if user[0] == 'pi':
            return 'sudo -u pi '
    return ''


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, on_start, on_stop, on_output):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_output = on_output

        self.id = str(id(self))
        self.process = None

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, command):
        if self.is_running() or not isinstance(command, str):
            raise InvalidOperation()

        cmd = get_cmd_prefix() + command
        self.process = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid)  # make a process group for this and children

        asyncio.create_task(self._communicate())

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

    async def _communicate(self):
        output_tasks = [
            asyncio.create_task(self._handle_output('stdout')),
            asyncio.create_task(self._handle_output('stderr')),
        ]

        # allow the output tasks to finish & flush
        await asyncio.wait(output_tasks)

        # process should be done now but await it to get exit code
        exit_code = await self.process.wait()
        self.process = None

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
