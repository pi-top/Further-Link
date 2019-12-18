import socket
from warnings import warn
import json
from cv2 import imencode
from base64 import b64encode

import __main__

ipc_channel_names = ['video']
ipc_channels = {}

try:
    for name in ipc_channel_names:
        ipc_filename = __main__.__file__.replace('.py', '.' + name + '.sock')
        ipc_channels[name] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ipc_channels[name].connect(ipc_filename)
        ipc_channels[name].settimeout(0.1)
except:
    print('Warning: Module further_link cannot be used in this context')


def send_image(frame):
    try:
        _, buffer = imencode('.jpg', frame)
        encoded = b64encode(buffer)
        message = b'video ' + encoded
        ipc_channels['video'].send(message)
    except:
        pass
