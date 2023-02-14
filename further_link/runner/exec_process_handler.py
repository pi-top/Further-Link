import logging
import os
import pathlib

from ..util.async_files import chmod, chown, create_directory, write_file
from ..util.user_config import (
    get_absolute_path,
    get_gid,
    get_uid,
    get_working_directory,
)
from .process_handler import ProcessHandler

dirname = pathlib.Path(__file__).parent.absolute()
further_link_module_path = os.path.join(dirname, "lib")


class ExecProcessHandler(ProcessHandler):
    async def _start(self, path, code=None, novncOptions={}):
        path = get_absolute_path(path, get_working_directory(self.user))

        # create path directories if they don't already exist
        logging.debug(f"{self.id} Creating working directory for exec")
        await create_directory(os.path.dirname(path), self.user)

        entrypoint = path if code is None else os.path.join(path, f"exec-{self.id}")

        # create a temporary file to execute if code is provided
        if code is not None:
            logging.debug(f"{self.id} Creating entrypoint for exec")
            await write_file(entrypoint, code)
            self._remove_entrypoint = entrypoint

        await chown(entrypoint, uid=get_uid(self.user), gid=get_gid(self.user))
        await chmod(entrypoint, 0o777)  # make it executable

        command = entrypoint

        work_dir = os.path.dirname(entrypoint)

        await super()._start(command, work_dir, novncOptions=novncOptions)

    async def _clean_up(self):
        try:
            if getattr(self, "_remove_entrypoint", None):
                os.remove(self._remove_entrypoint)
        except Exception as e:
            logging.exception(f"{self.id} Entrypoint Cleanup error: {e}")

        await super()._clean_up()
