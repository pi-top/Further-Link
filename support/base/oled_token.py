# coding=utf-8
import _thread
from time import sleep

from ptoled import PTOLEDDisplay


class Token(object):

    def display(self, token=None):
        '''
        传入token将自动显示token到小显示器上
        显示token
        :param token:
        :return:
        '''

        try:
            _thread.start_new_thread(self.__display__, (token,))
        except Exception as e:
            print(e)

    def __display__(self, token):
        ptoled = PTOLEDDisplay()
        ptoled.set_max_fps(1)

        canvas = ptoled.canvas
        canvas.set_font_size(25)

        canvas.clear()
        canvas.multiline_text((35, 16), token)
        ptoled.draw()
        sleep(30)
        canvas.clear()
        ptoled.draw()


if __name__ == '__main__':
    token = Token()
    token.display('1234')
    while True:
        pass
