import asyncio
import aiofiles


class InvalidOperation(Exception):
    pass


class ProcessHandler:
    def __init__(self, on_start, on_stop, on_output, work_dir="/tmp"):
        # loop = asyncio.get_event_loop()
        # asyncio.get_child_watcher().attach_loop(loop)
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_output = on_output
        self.work_dir = work_dir

        self.id = str(id(self))

    def __del__(self):
        if self.is_running():
            self.stop()

    async def start(self, script):
        if self.is_running() or not isinstance(script, str):
            raise InvalidOperation()

        main_filename = self._get_main_filename()
        async with aiofiles.open(main_filename, 'w+') as file:
            await file.write(script)

        command = 'python3 -u ' + main_filename
        self.process = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        asyncio.create_task(self._communicate())

        if self.on_start:
            await self.on_start()

    def is_running(self):
        return hasattr(self, 'process') and self.process is not None

    def stop(self):
        if not self.is_running():
            raise InvalidOperation()
        self.process.terminate()

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
        await asyncio.wait([
            asyncio.create_task(self._handle_output('stdout')),
            asyncio.create_task(self._handle_output('stderr'))
        ])

        exit_code = await self.process.wait()
        self.process = None
        await self._clean_up()

        if self.on_stop:
            await self.on_stop(exit_code)

    async def _handle_output(self, stream_name):
        stream = getattr(self.process, stream_name)
        while True:
            line = await stream.readline()
            output = line.decode(encoding='utf-8')
            if line:
                if self.on_output:
                    await self.on_output(stream_name, output)
            else:
                break

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

    async def _handle_ipc(self, channel):
        stream = getattr(self.process, stream_name)
        while True:
            line = await stream.readline()
            output = line.decode(encoding='utf-8')
            if line:
                if self.on_output:
                    await self.on_output(stream_name, output)
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
