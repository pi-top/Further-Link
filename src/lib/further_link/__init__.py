# This package is made available to user code running with further-link

import os
import socket
from base64 import b64encode
from PIL import Image
from io import BytesIO
from time import sleep

# __version__ made available for users
from .version import __version__


further_link_ipc_channels = {}


def get_temp_dir():
    return os.environ.get('FURTHER_LINK_TEMP_DIR', '/tmp')


def setup_ipc_channel(channel, retry=True):
    global further_link_ipc_channels

    if further_link_ipc_channels.get(channel):
        return

    try:
        ipc_filename = str(os.getpid()) + '.' + channel + '.sock'
        ipc_path = os.path.join(get_temp_dir(), ipc_filename)
        further_link_ipc_channels[channel] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        further_link_ipc_channels[channel].connect(ipc_path)
        further_link_ipc_channels[channel].settimeout(0.1)
    except Exception:
        further_link_ipc_channels[channel] = None
        if retry:
            sleep(0.1)  # wait for the ipc channels to start
            setup_ipc_channel(channel, retry=False)
        else:
            print(f'Warning: further_link {channel} channel is not available.')


# Taken from SDK, to avoid hard dependency
def _image_has_3_channels(image):
    return len(image.shape) == 3


def _image_rgb_bgr_convert(image):
    return image[:, :, ::-1]


def _pil_to_opencv(image):
    from numpy import array
    image_arr = array(image)

    if _image_has_3_channels(image_arr):
        # Array has 3 channel, do nothing
        image = _image_rgb_bgr_convert(image_arr)
    else:
        image = image_arr

    return image


def _opencv_to_pil(image):
    if len(image.shape) == 3:
        image = Image.fromarray(_image_rgb_bgr_convert(image))
    else:
        # Not 3 channel, just convert
        image = Image.fromarray(image)

    return image


def send_image(frame, format=None):
    setup_ipc_channel('video')

    if format is not None:
        print("The 'format' parameter is no longer required in this function. Both PIL and OpenCV formats can be used without specifying which.")

    if not isinstance(frame, Image.Image):
        frame = _opencv_to_pil(frame)

    try:
        buffered = BytesIO()
        frame.save(buffered, format="JPEG", optimize=True)
        encoded = b64encode(buffered.getvalue())
        message = encoded + b' endvideo '

        total_sent = 0
        while total_sent < len(message):
            sent = further_link_ipc_channels['video'].send(message[total_sent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            total_sent = total_sent + sent
    except Exception:
        pass
