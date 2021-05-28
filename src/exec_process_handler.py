import os
import pathlib
import aiofiles

from .process_handler import ProcessHandler, InvalidOperation
from .user_config import get_working_directory

dirname = pathlib.Path(__file__).parent.absolute()
further_link_module_path = os.path.join(dirname, 'lib')


class ExecProcessHandler(ProcessHandler):
    async def start(self, script=None, path=False):
        entrypoint = await self._get_entrypoint(script, path)
        self._remove_entrypoint = entrypoint if script is not None else None

        os.chmod(entrypoint, 0o777)  # executable

        print(entrypoint)

        command = entrypoint

        work_dir = os.path.dirname(entrypoint)

        await super().start(command, work_dir)

    async def _get_entrypoint(self, script=None, path=None):
        if isinstance(path, str):
            # path is absolute or relative to work_dir
            first_char = path[0]
            if first_char != '/':
                further_work_dir = get_working_directory(self.user)
                path = os.path.join(further_work_dir, path)

            path_dirs = path if isinstance(
                script, str) else os.path.dirname(path)

            # if there's a script to create, create path dirs for it to go in
            if not os.path.exists(path_dirs) and isinstance(script, str):
                os.makedirs(path_dirs, exist_ok=True)

        if isinstance(script, str):
            # write script to file, at path if given, otherwise temp
            entrypoint = self._get_script_filename(path)
            async with aiofiles.open(entrypoint, 'w+') as file:
                await file.write(script)

            return entrypoint

        if path is not None:
            return path

        raise InvalidOperation()

    def _get_script_filename(self, path=None):
        dir = path if isinstance(path, str) else self.temp_dir
        return dir + '/' + self.id + '.py'
