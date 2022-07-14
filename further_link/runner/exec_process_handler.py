import os
import pathlib

import aiofiles

from ..util.user_config import get_absolute_path, get_working_directory
from .process_handler import ProcessHandler

dirname = pathlib.Path(__file__).parent.absolute()
further_link_module_path = os.path.join(dirname, "lib")


class ExecProcessHandler(ProcessHandler):
    async def start(self, path, code=None, novnc=False):
        path = get_absolute_path(path, get_working_directory(self.user))

        # create path directories if they don't already exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        entrypoint = path if code is None else os.path.join(path, f"exec-{self.id}")

        # create a temporary file to execute if code is provided
        if code is not None:
            async with aiofiles.open(entrypoint, "w+") as file:
                await file.write(code)
            self._remove_entrypoint = entrypoint

        os.chmod(entrypoint, 0o777)  # make it executable

        command = entrypoint

        work_dir = os.path.dirname(entrypoint)

        await super().start(command, work_dir, novnc=novnc)

    async def _clean_up(self):
        try:
            if self._remove_entrypoint is not None:
                os.remove(self._remove_entrypoint)
        except Exception:
            pass

        await super()._clean_up()
