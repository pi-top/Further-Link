# This package is made available to user code running with further-link

import os
import socket
from base64 import b64encode

import __main__

try:
    from cv2 import imencode
    from PIL import Image
except ImportError as e:
    print(e)

# __version__ made available for users
from .version import __version__


ipc_channel_names = ['video']
ipc_channels = {}

main_filename = os.path.basename(__main__.__file__)


def get_temp_dir():
    return os.environ.get('FURTHER_LINK_TEMP_DIR', '/tmp')


try:
    for name in ipc_channel_names:
        ipc_filename = main_filename.replace('.py', '.' + name + '.sock')
        ipc_path = os.path.join(get_temp_dir(), ipc_filename)
        ipc_channels[name] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ipc_channels[name].connect(ipc_path)
        ipc_channels[name].settimeout(0.1)
except Exception:
    print('Warning: Module further_link cannot be used in this context')


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
    if format is not None:
        print("The 'format' parameter is no longer required in this function. Both PIL and OpenCV formats can be used without specifying which.")

    if isinstance(frame, Image.Image):
        frame = _pil_to_opencv(frame)

    try:
        _, buffer = imencode('.jpg', frame)
        encoded = b64encode(buffer)
        message = encoded + b' endvideo '

        total_sent = 0
        while total_sent < len(message):
            sent = ipc_channels['video'].send(message[total_sent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            total_sent = total_sent + sent
    except Exception:
        pass
