from signal import pause

from ptpma import PMACamera

from further_link import send_image

cam = PMACamera()

cam.start_handling_frames(send_image)
pause()
