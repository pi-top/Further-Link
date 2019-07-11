# coding=utf-8
import _thread
import logging

log = logging.getLogger(__name__)


class Token(object):
    def display(self, token=None):
        '''
        display show on the oled
        :param token:
        :return:
        '''

        try:

            if not token:
                return False
            log.info("the oled Token [" + token + "]")
            _thread.start_new_thread(self.__display__, (token,))
        except Exception as e:
            log.error("oled display token error")
            return False

    def __display__(self, token):
        try:
            from ptoled import PTOLEDDisplay
            ptoled = PTOLEDDisplay()
            ptoled.set_max_fps(1)

            canvas = ptoled.canvas
            canvas.set_font_size(25)

            canvas.clear()
            canvas.multiline_text((35, 16), token)
            ptoled.draw()
        except:
            log.error("oled display token error")


if __name__ == '__main__':
    token = Token()
    token.display('1234')
    while True:
        pass
