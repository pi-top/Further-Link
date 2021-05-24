from signal import pause
from pitop import Pitop, Camera, DriveController
from further_link import KeyboardButton, send_image

robot = Pitop()
robot.add_component(DriveController(left_motor_port="M3", right_motor_port="M0"))
robot.add_component(Camera())

robot.camera.on_frame = send_image

up = KeyboardButton('ArrowUp')
down = KeyboardButton('ArrowDown')
left = KeyboardButton('ArrowLeft')
right = KeyboardButton('ArrowRight')

up.when_pressed = lambda: robot.drive.forward(1, hold=True)
up.when_released = lambda: robot.drive.stop()

down.when_pressed = lambda: robot.drive.forward(-1, hold=True)
down.when_released = lambda: robot.drive.stop()

left.when_pressed = lambda: robot.drive.left(1)
left.when_released = lambda: robot.drive.left(0)

right.when_pressed = lambda: robot.drive.right(1)
right.when_released = lambda: robot.drive.right(0)

pause()
