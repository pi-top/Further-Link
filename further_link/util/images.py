from base64 import b64encode
from io import BytesIO

from PIL import Image


def _image_rgb_bgr_convert(image):
    return image[:, :, ::-1]


def _opencv_to_pil(image):
    if len(image.shape) == 3:
        image = Image.fromarray(_image_rgb_bgr_convert(image))
    else:
        # Not 3 channel, just convert
        image = Image.fromarray(image)

    return image


def base64_encode(frame):
    if not isinstance(frame, Image.Image):
        frame = _opencv_to_pil(frame)

    buffered = BytesIO()
    frame.save(buffered, format="JPEG", optimize=True)
    encoded = b64encode(buffered.getvalue())

    return encoded
