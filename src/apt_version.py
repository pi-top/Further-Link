import json
from shlex import split
from subprocess import check_output, CalledProcessError
import re

from aiohttp import web


async def apt_version(request):
    version = apt_cache_installed(request.match_info['pkg'])
    return web.Response(text=json.dumps({'version': version}))


def apt_cache_installed(pkg_name):
    try:
        command = split(f'apt-cache policy {pkg_name}')
        output = check_output(command).decode("utf-8")
        match = re.search("Installed: (.*)", output)
        return match.group(1) if match else None
    except (CalledProcessError, FileNotFoundError):
        return None
