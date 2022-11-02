from ..util.upload import create_directory
from ..util.user_config import get_absolute_path, get_shell, get_working_directory
from .process_handler import ProcessHandler


class ShellProcessHandler(ProcessHandler):
    async def _start(self, path, code=None, novncOptions={}):
        work_dir = get_absolute_path(path, get_working_directory(self.user))

        # create work dir if it doesn't already exist
        await create_directory(work_dir, self.user)

        await super()._start(get_shell(self.user), work_dir, novncOptions=novncOptions)
