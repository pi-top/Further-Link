from pitop import Camera
from further_link import send_image
from signal import pause

cam = Camera()
cam.start_handling_frames(send_image)
pause()
