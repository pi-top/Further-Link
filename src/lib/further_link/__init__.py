# This package is made available to code running with further-link

import socket
from base64 import b64encode

import __main__
from .version import __version__

ipc_channel_names = ['video']
ipc_channels = {}

try:
    for name in ipc_channel_names:
        ipc_filename = __main__.__file__.replace('.py', '.' + name + '.sock')
        ipc_channels[name] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ipc_channels[name].connect(ipc_filename)
        ipc_channels[name].settimeout(0.1)
except Exception:
    print('Warning: Module further_link cannot be used in this context')


def send_image(frame):
    try:
        from cv2 import imencode
    except ImportError as e:
        print(e)
        return

    try:
        _, buffer = imencode('.jpg', frame)
        encoded = b64encode(buffer)
        message = b'video ' + encoded

        total_sent = 0
        while total_sent < len(message):
            sent = ipc_channels['video'].send(message[total_sent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            total_sent = total_sent + sent
    except:
        pass
