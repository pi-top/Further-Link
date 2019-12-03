import cv2
from camera import PMACamera
from further import send_image
from signal import pause

cam = PMACamera()

cam.start_handling_frames(send_image)
pause()
