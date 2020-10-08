import asyncio
import pwd
import os
import signal
import pty

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
    def __init__(self, on_start, on_stop, on_output, work_dir='/tmp'):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_output = on_output
        self.work_dir = work_dir

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

        asyncio.create_task(self._ipc_communicate())

        # communicate through a pty for terminal 'cooked mode' behaviour
        master, slave = pty.openpty()
        self.pty_master = await aiofiles.open(master, 'w+b', 0)
        self.pty_slave = await aiofiles.open(slave, 'r+b', 0)

        command = get_cmd_prefix() + 'python3 -u ' + main_filename
        self.process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdin=self.pty_slave,
            stdout=self.pty_slave,
            stderr=self.pty_slave,
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

        await self.pty_master.write(content.encode('utf-8'))

    def _get_main_filename(self):
        return self.work_dir + '/' + self.id + '.py'

    def _get_ipc_filename(self, channel):
        return self.work_dir + '/' + self.id + '.' + channel + '.sock'

    async def _ipc_communicate(self):
        self.ipc_tasks = []
        for name in IPC_CHANNELS:
            self.ipc_tasks.append(asyncio.create_task(
                self._handle_ipc(name)
            ))

    async def _process_communicate(self):
        output_tasks = [
            asyncio.create_task(self._handle_output(self.pty_master)),
        ]

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

    async def _handle_output(self, stream):
        while True:
            data = await stream.read(4096)
            if data == b'':
                break

            output = data.decode(encoding='utf-8')
            if self.on_output:
                await self.on_output('stdout', output)

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
            os.remove(self._get_main_filename())

            self.pty_master.close()
            self.pty_slave.close()
            os.remove(self.pty_master)
            os.remove(self.pty_slave)

            for name in IPC_CHANNELS:
                try:
                    os.remove(self._get_ipc_filename(name))
                except:
                    pass
        except:
            pass
