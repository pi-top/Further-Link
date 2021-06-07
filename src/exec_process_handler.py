import os
import pathlib
import aiofiles

from .process_handler import ProcessHandler
from .util.user_config import get_working_directory, get_absolute_path

dirname = pathlib.Path(__file__).parent.absolute()
further_link_module_path = os.path.join(dirname, 'lib')


class ExecProcessHandler(ProcessHandler):
    async def start(self, path, code=None):
        entrypoint = await self._get_entrypoint(path, code)
        self._remove_entrypoint = entrypoint if code is not None else None

        os.chmod(entrypoint, 0o777)  # make it executable

        command = entrypoint

        work_dir = os.path.dirname(entrypoint)

        await super().start(command, work_dir)

    async def _get_entrypoint(self, path, code=None):
        path = get_absolute_path(path, get_working_directory(self.user))

        # with no code path should point to a file, otherwise take its dir
        path_dirs = path if isinstance(code, str) else os.path.dirname(path)

        # create path dirs if they don't already exist
        os.makedirs(path_dirs, exist_ok=True)

        if code is None:
            return path

        # write script to file, at path if given, otherwise temp
        entrypoint = self._get_script_filename(path)
        async with aiofiles.open(entrypoint, 'w+') as file:
            await file.write(code)

        return entrypoint

    def _get_script_filename(self, dir):
        return dir + '/' + self.id + '.py'
