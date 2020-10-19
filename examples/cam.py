import cv2
from ptpma import PMACamera
from further_link import send_image
from signal import pause

cam = PMACamera()

cam.start_handling_frames(send_image)
pause()
