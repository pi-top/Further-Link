import json
import re
from os import environ
from shlex import split
from subprocess import run

from aiohttp import web


async def apt_version(request):
    version = apt_cache_installed(request.match_info["pkg"])
    return web.Response(text=json.dumps({"version": version}))


def apt_cache_installed(pkg_name):
    try:
        command = f"apt-cache policy {pkg_name}"
        output = run_command(command)
        match = re.search("Installed: (.*)", output)
        return match.group(1) if match else None
    except Exception:
        return None


def run_command(command_str):
    def __get_env():
        env = environ.copy()
        # Print output of commands in english
        env["LANG"] = "en_US.UTF-8"
        return env

    try:
        resp = run(
            split(command_str),
            check=False,
            capture_output=True,
            timeout=5,
            env=__get_env(),
        )
        return str(resp.stdout, "utf8")
    except Exception:
        return None
