from base64 import b64encode
from io import BytesIO

from PIL import Image

from further_link.util.ipc import ipc_send


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
        print(
            "The 'format' parameter is no longer required in this function. Both PIL and OpenCV formats can be used without specifying which."
        )

    if not isinstance(frame, Image.Image):
        frame = _opencv_to_pil(frame)

    try:
        buffered = BytesIO()
        frame.save(buffered, format="JPEG", optimize=True)
        encoded = b64encode(buffered.getvalue())
        ipc_send("video", encoded)
    except Exception:
        pass
