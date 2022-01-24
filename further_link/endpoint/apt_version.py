import json
import re

from aiohttp import web
from pitop.common.command_runner import run_command


async def apt_version(request):
    version = apt_cache_installed(request.match_info["pkg"])
    return web.Response(text=json.dumps({"version": version}))


def apt_cache_installed(pkg_name):
    try:
        command = f"apt-cache policy {pkg_name}"
        output = run_command(command, timeout=5)
        match = re.search("Installed: (.*)", output)
        return match.group(1) if match else None
    except Exception:
        return None
