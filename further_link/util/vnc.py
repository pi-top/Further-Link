import asyncio
import logging
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from further_link.util.display_activity_monitor import DisplayActivityMonitor
from further_link.util.ssl_context import SslFiles, cert, private_key

display_activity_monitors = {}

VNC_CERTIFICATE_PATH = "/tmp/.further_link.vnc_ssl.pem"


class VncConnectionDetails:
    def __init__(self, url) -> None:
        self._parsed_url = urlparse(url)

    @property
    def port(self):
        return self._parsed_url.port

    @property
    def path(self):
        return f"{self._parsed_url.path}?{self._parsed_url.query}"


async def start_vnc(id: int, on_display_activity: Callable) -> None:
    proc = await asyncio.create_subprocess_shell(
        f"further-link-vnc start {id} {VNC_CERTIFICATE_PATH}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    logging.info(f"Starting further-link-vnc on display '{id}'")
    await proc.wait()

    activity_monitor = DisplayActivityMonitor(id)

    async def on_monitor_activity():
        if not callable(on_display_activity):
            return

        connection_details = await vnc_connection_details(id)
        if connection_details:
            await on_display_activity(connection_details)

    display_activity_monitors[id] = activity_monitor
    activity_monitor.on_display_activity = on_monitor_activity
    activity_monitor.start()


async def stop_vnc(id: int) -> None:
    proc = await asyncio.create_subprocess_shell(
        f"further-link-vnc stop {id}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logging.info(f"Stopping further-link-vnc on display '{id}'")
    await proc.wait()

    activity_monitor = display_activity_monitors.get(id)
    if activity_monitor:
        await activity_monitor.stop()
        display_activity_monitors.pop(id)


async def vnc_connection_details(id: int):
    proc = await asyncio.create_subprocess_shell(
        f"further-link-vnc url {id}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    novnc_url, _ = await proc.communicate()
    return VncConnectionDetails(url=novnc_url.decode().strip())


def create_ssl_certificate() -> None:
    vnc_cert = Path(VNC_CERTIFICATE_PATH)
    if vnc_cert.exists():
        return
    vnc_cert.touch(exist_ok=True)

    ssl_files = SslFiles()
    with open(VNC_CERTIFICATE_PATH, "w") as f:
        for data in (cert(ssl_files), private_key(ssl_files)):
            f.write(data.decode("utf-8"))
