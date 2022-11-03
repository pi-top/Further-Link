import asyncio
import logging
from pty import openpty

import aiofiles

from ..util.async_files import chown, close
from ..util.async_helpers import timeout
from ..util.terminal import set_winsize
from ..util.user_config import get_gid, get_uid


class Pty:
    @classmethod
    async def create(cls, user):
        self = cls()
        self.front_fd, self.back_fd = openpty()

        # on some distros process user must own 'back', otherwise you get:
        # cannot set terminal process group (-1): Inappropriate ioctl for device
        await chown(self.back_fd, get_uid(user), get_gid(user))

        self.front = await aiofiles.open(self.front_fd, "w+b", 0)
        self.back = await aiofiles.open(self.back_fd, "r+b", 0)

        return self

    def set_winsize(self, rows, cols):
        set_winsize(self.back_fd, 4, 60)

    async def write(self, content_bytes):
        await self.front.write(content_bytes)

    async def clean_up(self):
        logging.debug("PTY Closing master")
        await self._clean_up_end(self.front, self.front_fd)
        logging.debug("PTY Closing slave")
        await self._clean_up_end(self.back, self.back_fd)
        logging.debug("PTY Cleanup complete")

    async def _clean_up_end(self, file, fd):
        # closing sometimes hangs so use a timeout and try closing fd also
        async def close_file():
            try:
                logging.debug("PTY Closing file")
                await file.close()
            except Exception as e:
                logging.debug(f"PTY Close file error: {e}")

        close_file_task = asyncio.create_task(close_file())
        done = await timeout(close_file_task, 0.1)
        if close_file_task not in done:
            logging.debug("PTY Close file timed out")

        async def close_fd():
            try:
                logging.debug("PTY Closing fd")
                await close(fd)
            except Exception as e:
                logging.debug(f"PTY Close fd error: {e}")

        close_fd_task = asyncio.create_task(close_fd())
        done = await timeout(close_fd_task, 0.1)
        if close_fd_task not in done:
            logging.debug("PTY Close fd timed out")
