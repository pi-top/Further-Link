from signal import pause

from pitop import Camera

from further_link import send_image

cam = Camera()
cam.start_handling_frames(send_image)
pause()
