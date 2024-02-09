import asyncio
import os
import socket
from time import sleep

from .sdk import Singleton

# buffer limit for our socket read streams. this is the limit for the size on an
# ipc message that can be sent.it's not too large to as to support sending at a
# good rate on a slow network
MAX_BUFFER = 4096


class FurtherLinkIPCClientCache(metaclass=Singleton):
    def __init__(self):
        self.ipc_clients = {}
        self.async_ipc_clients = {}


def _get_temp_dir():
    return os.environ.get("FURTHER_LINK_TEMP_DIR", "/tmp")


# pgid is used to match up the ipc servers and clients, as it's something the
# server knows about the process and the process can look up by itself
def _get_ipc_channel_key(channel, pgid=None):
    if pgid is None:
        pgid = os.getpgid(os.getpid())
    return str(pgid) + "." + str(channel)


def _get_ipc_filepath(channel, pgid=None):
    channel_key = _get_ipc_channel_key(channel, pgid=pgid)
    return os.path.join(_get_temp_dir(), channel_key + ".sock")


def _collect_ipc_messages(channel, incomplete, data):
    # split data on channel message terminator and return list of complete
    # messages and left over incomplete portion
    # TODO consider a message-size header based solution instead of delimiter
    complete = []
    # split on spaces (not empty split() which ignores repeat spaces)
    tokens = data.decode("utf-8").strip().split(" ")
    new_message = True
    for i, token in enumerate(tokens):
        if token == "end" + channel:  # message terminator
            if len(incomplete) > 0:
                complete.append(incomplete)
                incomplete = ""
            new_message = True
        elif new_message:
            incomplete += token  # no space in front of first part
            new_message = False
        else:
            incomplete += " " + token  # reinsert spaces into rest
    return complete, incomplete


def start_ipc_server(channel, handle_message=None, pgid=None, kBps=128):
    buffer_time = 0 if kBps == 0 else MAX_BUFFER / kBps / 1000

    ipc_filepath = _get_ipc_filepath(channel, pgid=pgid)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(ipc_filepath)
    os.chmod(ipc_filepath, 0o666)  # ensures pi user can use this too

    while True:
        server.listen(1)
        conn, addr = server.accept()

        # set read buffer size to match our buffer size
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, MAX_BUFFER)

        # if we needed to handle multiple connections we would need to spawn a
        # thread for the below connection handler loop
        incomplete_message = ""
        while True:
            # read up to the end of the socket buffer
            data = conn.recv(MAX_BUFFER)

            if not data or data == b"":
                break

            # split data on channel message terminator and return list of complete
            # messages and left over incomplete portion
            complete_messages, incomplete_message = _collect_ipc_messages(
                channel, incomplete_message, data
            )

            if handle_message:
                for c in complete_messages:
                    handle_message(c)

            sleep(buffer_time)


async def async_start_ipc_server(channel, handle_message=None, pgid=None, kBps=128):
    buffer_time = 0 if kBps == 0 else MAX_BUFFER / kBps / 1000

    async def handle_connection(reader, _):
        incomplete_message = ""

        while True:
            # read up to the end of the socket buffer
            data = await reader.read(MAX_BUFFER)

            if data == b"":
                break

            # split data on channel message terminator and return list of complete
            # messages and left over incomplete portion
            complete_messages, incomplete_message = _collect_ipc_messages(
                channel, incomplete_message, data
            )

            if handle_message:
                for c in complete_messages:
                    await handle_message(c)

            await asyncio.sleep(buffer_time)

    ipc_filepath = _get_ipc_filepath(channel, pgid=pgid)
    # set the read buffer size when creating the server
    server = await asyncio.start_unix_server(
        handle_connection, path=ipc_filepath, limit=MAX_BUFFER
    )
    os.chmod(ipc_filepath, 0o666)  # ensures pi user can use this too
    return server


def _connect_ipc_client(channel, retry=True, pgid=None):
    channel_key = _get_ipc_channel_key(channel, pgid)
    sock = FurtherLinkIPCClientCache().ipc_clients.get(channel_key)

    if sock:
        return sock

    try:
        ipc_path = _get_ipc_filepath(channel, pgid=pgid)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(ipc_path)
        sock.settimeout(0.1)
        FurtherLinkIPCClientCache().ipc_clients[channel_key] = sock
    except Exception:
        FurtherLinkIPCClientCache().ipc_clients[channel_key] = None
        if retry:
            sleep(0.1)  # wait for the ipc channels to start
            _connect_ipc_client(channel, retry=False, pgid=pgid)
        else:
            print(f"Warning: further_link {channel} channel is not available.")

    return sock


def ipc_send(channel, message, pgid=None):
    if not isinstance(message, bytes):
        message = message.encode()
    sock = _connect_ipc_client(channel, pgid=pgid)
    message = message + f" end{channel} ".encode()

    total_sent = 0
    while total_sent < len(message):
        sent = sock.send(message[total_sent:])
        if sent == 0:
            print(f"Warning: further_link {channel} channel disconnected.")
        total_sent = total_sent + sent


async def _async_connect_ipc_client(channel, retry=True, pgid=None):
    channel_key = _get_ipc_channel_key(channel, pgid)
    sock = FurtherLinkIPCClientCache().async_ipc_clients.get(channel_key)

    if sock and not sock[1].is_closing():
        return sock

    try:
        ipc_path = _get_ipc_filepath(channel, pgid=pgid)
        sock = await asyncio.open_unix_connection(path=ipc_path)
        FurtherLinkIPCClientCache().async_ipc_clients[channel_key] = sock
    except Exception:
        FurtherLinkIPCClientCache().async_ipc_clients[channel_key] = None
        if retry:
            sleep(0.1)  # wait for the ipc channels to start
            await _async_connect_ipc_client(channel, retry=False, pgid=pgid)
        else:
            print(f"Warning: further_link {channel} channel is not available.")

    return sock


async def async_ipc_send(channel, message, pgid=None):
    if not isinstance(message, bytes):
        message = message.encode()
    try:
        reader, writer = await _async_connect_ipc_client(channel, pgid=pgid)
        message = message + f" end{channel} ".encode()
        writer.write(message)
        await writer.drain()
    except Exception:
        print(f"Warning: further_link {channel} channel disconnected.")


def ipc_cleanup(channel, pgid=None):
    # no async option - aiofiles.os.remove not released to debian buster
    # os.remove should not block significantly, just fires a single syscall
    os.remove(_get_ipc_filepath(channel, pgid=pgid))
