from .process_handler import ProcessHandler
from .user_config import get_shell, get_working_directory, get_absolute_path


class ShellProcessHandler(ProcessHandler):
    async def start(self, path, code=None):
        work_dir = get_absolute_path(path, get_working_directory(self.user))
        await super().start(get_shell(self.user), work_dir)
