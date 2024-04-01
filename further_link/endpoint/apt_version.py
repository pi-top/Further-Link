import json
import re

from aiohttp import web

from ..util.sdk import run_command


def _apt_version_dict(package):
    return {"version": apt_cache_installed(package)}


async def apt_version_bt(device, char_uuid, value, characteristic_to_report_on):
    version = _apt_version_dict(value.decode())
    await device.write_value(json.dumps(version), characteristic_to_report_on)


async def apt_version(request):
    version = _apt_version_dict(request.match_info["pkg"])
    return web.Response(text=json.dumps(version))


def apt_cache_installed(pkg_name):
    try:
        command = f"apt-cache policy {pkg_name}"
        output = run_command(command)
        match = re.search("Installed: (.*)", output)
        return match.group(1) if match else None
    except Exception:
        return None
