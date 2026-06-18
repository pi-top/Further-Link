import logging
import os
import pathlib
import shlex

import aiofiles

from ..util.upload import create_directory
from ..util.user_config import (
    get_absolute_path,
    get_gid,
    get_uid,
    get_working_directory,
)
from .process_handler import ProcessHandler

dirname = pathlib.Path(__file__).parent.absolute()


class PyProcessHandler(ProcessHandler):
    async def _start(self, path, code=None, novncOptions={}):
        path = get_absolute_path(path, get_working_directory(self.user))

        # create path directories if they don't already exist
        create_directory(os.path.dirname(path), self.user)

        entrypoint = path if code is None else os.path.join(path, f"{self.id}.py")

        # create a temporary file to execute if code is provided
        if code is not None:
            async with aiofiles.open(entrypoint, "w+") as file:
                await file.write(code)
            self._remove_entrypoint = entrypoint

        # Check for venv in environment
        venv = os.environ.get("FURTHER_VENV")
        env = {}

        if venv and os.path.isfile(os.path.join(venv, "bin", "python3")):
            env = {
                "VIRTUAL_ENV": venv,
                "PATH": f"{venv}/bin:{os.environ.get('PATH', '')}",
            }

        command = f"python3 -u {shlex.quote(entrypoint)}"

        os.chown(entrypoint, uid=get_uid(self.user), gid=get_gid(self.user))

        work_dir = os.path.dirname(entrypoint)

        await super()._start(command, work_dir, env=env, novncOptions=novncOptions)

    async def _clean_up(self):
        try:
            if getattr(self, "_remove_entrypoint", None):
                os.remove(self._remove_entrypoint)
        except Exception as e:
            logging.exception(f"{self.id} Entrypoint Cleanup error: {e}")

        await super()._clean_up()
