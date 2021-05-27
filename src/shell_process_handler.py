from .process_handler import ProcessHandler
from .user_config import get_shell


class ShellProcessHandler(ProcessHandler):
    async def start(self):
        await super().start(get_shell(self.user))
