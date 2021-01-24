# This package is made available to user code running with further-link

# __version__ made available for users
from .version import __version__

from base64 import b64encode
import numpy as np
from os import environ, path
from PIL import Image
from socket import (
    socket,
    AF_UNIX,
    SOCK_STREAM,
)

import __main__

ipc_channel_names = ['video']
ipc_channels = {}

main_filename = path.basename(__main__.__file__)


def get_temp_dir():
    return environ.get('FURTHER_LINK_TEMP_DIR', '/tmp')


try:
    for name in ipc_channel_names:
        ipc_filename = main_filename.replace('.py', '.' + name + '.sock')
        ipc_path = path.join(get_temp_dir(), ipc_filename)
        ipc_channels[name] = socket(AF_UNIX, SOCK_STREAM)
        ipc_channels[name].connect(ipc_path)
        ipc_channels[name].settimeout(0.1)
except Exception:
    print('Warning: Module further_link cannot be used in this context')


# Taken from SDK, to avoid hard dependency
# TODO: evaluate how Further Link and SDK co-exist
def _pil_to_opencv(image):
    return np.array(image)[:, :, ::-1]


def _opencv_to_pil(image):
    if len(image.shape) == 3:
        return Image.fromarray(image[:, :, ::-1])
    else:
        return Image.fromarray(image[:, :])


def send_image(frame, format="PIL"):
    try:
        from cv2 import imencode
    except ImportError as e:
        print(e)
        return

    if format == "PIL":
        frame = _pil_to_opencv(frame)

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
    except Exception:
        pass
