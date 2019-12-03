import socket
import json
from base64 import b64encode
from cv2 import imencode

import __main__

ipc_filename = __main__.__file__.replace('.py', '.sock')

ipc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
ipc.connect(ipc_filename)

def send_image(frame):
    global ipc

    try:
        _, buffer = imencode('.jpg', frame)
        encoded = b64encode(buffer)
        message = b'furtherVideo ' + encoded
        ipc.send(message)
    except Exception as e:
        print('error: ', e)
