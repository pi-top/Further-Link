import os
import socket
import asyncio
from time import sleep


IPC_CHANNELS = [
    'video',
    'keyevents'
]
_further_link_ipc_channels = {}
_further_link_async_ipc_channels = {}


def _get_temp_dir():
    return os.environ.get('FURTHER_LINK_TEMP_DIR', '/tmp')


def _get_ipc_filepath(channel, pgid=None):
    if pgid is None:
        pgid = os.getpgid(os.getpid())

    ipc_filename = str(pgid) + '.' + channel + '.sock'
    return os.path.join(_get_temp_dir(), ipc_filename)


def _collect_ipc_messages(channel, incomplete, data):
    # split data on channel message terminator and return list of complete
    # messages and left over incomplete portion
    complete = []
    tokens = data.decode('utf-8').strip().split(' ')  # NOT split()
    print('tokens', tokens)
    for i, token in enumerate(tokens):
        new_message = False
        if token == 'end' + channel:  # end of message
            if len(incomplete) > 0:
                complete.append(incomplete)
                incomplete = ''
            new_message = True
        elif i == 0 or new_message:
            incomplete += token  # no space in front of first part
            new_message = False
        else:
            incomplete += ' ' + token  # reinsert spaces into rest
    return complete, incomplete


def start_ipc_server(channel, handle_message=None, pgid=None):
    ipc_filepath = _get_ipc_filepath(channel, pgid=pgid)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(ipc_filepath)
    os.chmod(ipc_filepath, 0o666)  # ensures pi user can use this too

    incomplete = ''
    while True:
        server.listen(1)
        conn, addr = server.accept()
        data = conn.recv(4096)
        print(data)  # TODO

        if not data or data == b'':
            break

        complete, incomplete = _collect_ipc_messages(channel, incomplete,
                                                     data)
        if handle_message:
            for c in complete:
                handle_message(c)


async def async_start_ipc_server(channel, handle_message=None, pgid=None):
    async def handle_connection(reader, _):
        incomplete = ''
        while True:
            data = await reader.read(4096)
            print('data', data)
            if data == b'':
                break

            complete, incomplete = _collect_ipc_messages(channel, incomplete,
                                                         data)
            print(complete, incomplete)
            if handle_message:
                for c in complete:
                    await handle_message(c)

    ipc_filepath = _get_ipc_filepath(channel, pgid=pgid)
    await asyncio.start_unix_server(handle_connection, path=ipc_filepath)
    os.chmod(ipc_filepath, 0o666)  # ensures pi user can use this too


def _connect_ipc_client(channel, retry=True, pgid=None):
    global _further_link_ipc_channels
    sock = None

    if _further_link_ipc_channels.get(channel):
        return sock

    try:
        ipc_path = _get_ipc_filepath(channel, pgid=pgid)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        _further_link_ipc_channels[channel] = sock
        _further_link_ipc_channels[channel].connect(ipc_path)
        _further_link_ipc_channels[channel].settimeout(0.1)
    except Exception:
        _further_link_ipc_channels[channel] = None
        if retry:
            sleep(0.1)  # wait for the ipc channels to start
            _connect_ipc_client(channel, retry=False, pgid=pgid)
        else:
            print(f'Warning: further_link {channel} channel is not available.')

    return sock


def ipc_send(channel, message, pgid=None):
    sock = _connect_ipc_client(channel, pgid=pgid)
    message = message + f' end{channel} '.encode()

    total_sent = 0
    while total_sent < len(message):
        sent = sock.send(message[total_sent:])
        if sent == 0:
            print(f'Warning: further_link {channel} channel disconnected.')
        total_sent = total_sent + sent


async def _async_connect_ipc_client(channel, retry=True, pgid=None):
    global _further_link_async_ipc_channels
    conn = None

    if _further_link_async_ipc_channels.get(channel):
        return conn

    try:
        ipc_path = _get_ipc_filepath(channel, pgid=pgid)
        conn = asyncio.open_unix_connection(path=ipc_path)
        _further_link_async_ipc_channels[channel] = conn
    except Exception:
        _further_link_async_ipc_channels[channel] = None
        if retry:
            sleep(0.1)  # wait for the ipc channels to start
            _async_connect_ipc_client(channel, retry=False, pgid=pgid)
        else:
            print(f'Warning: further_link {channel} channel is not available.')

    return conn


async def async_ipc_send(channel, message, pgid):
    reader, writer = _async_connect_ipc_client(channel, pgid=pgid)
    message = message + f' end{channel} '.encode()
    try:
        writer.write(message)
        await writer.drain()
    except Exception:
        print(f'Warning: further_link {channel} channel disconnected.')


def ipc_cleanup(channel, pgid=None):
    try:
        os.remove(_get_ipc_filepath(channel, pgid=pgid))
    except Exception:
        pass
