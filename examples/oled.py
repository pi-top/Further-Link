from ptoled import PTOLEDDisplay
from time import sleep

oled_screen = PTOLEDDisplay()
oled_screen.draw_multiline_text('hello world!')
sleep(5)
