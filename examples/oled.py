from time import sleep

from ptoled import PTOLEDDisplay

oled_screen = PTOLEDDisplay()
oled_screen.draw_multiline_text("hello world!")
sleep(5)
