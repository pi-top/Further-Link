from threading import Thread
import atexit

from .ipc import start_ipc_server, ipc_send, ipc_cleanup

buttons = {}


def on_key_event(message):
    key, event = message.split(' ')
    button = buttons.get(key)
    if button:
        if event == 'keydown':
            button._on_press()
        elif event == 'keyup':
            button._on_release()


listening = False


def start_listener():
    global listening
    if not listening:
        Thread(target=start_ipc_server,
               args=('keyevent', on_key_event)).start()
        atexit.register(cleanup_listener)
        listening = True


def cleanup_listener():
    ipc_cleanup('keyevent')


class KeyboardButton:
    def __init__(self, key):
        self.key = key
        self.pressed_method = None
        self.released_method = None
        self.__key_pressed = False

        buttons[key] = self
        start_listener()
        ipc_send('keylisten', key)

    def _on_press(self):
        self.__key_pressed = True
        if self.pressed_method is not None:
            self.pressed_method()

    def _on_release(self):
        self.__key_pressed = False
        if self.released_method is not None:
            self.released_method()

    @property
    def when_pressed(self):
        """Get or set the 'when pressed' button state callback function. When
        set, this callback function will be invoked when this event happens.

        :type callback: Function
        :param callback:
            Callback function to run when a button is pressed.
        """

    @when_pressed.setter
    def when_pressed(self, method=None):
        if method is None:
            raise "Error: no method assigned"
        self.pressed_method = method

    @property
    def when_released(self):
        """Get or set the 'when released' button state callback function. When
        set, this callback function will be invoked when this event happens.

        :type callback: Function
        :param callback:
            Callback function to run when a button is released.
        """

    @when_released.setter
    def when_released(self, method=None):
        if method is None:
            raise "Error: no method assigned"
        self.released_method = method

    @property
    def is_pressed(self) -> bool:
        """Get or set the button state as a boolean value.

        :rtype: bool
        """
        if self.__key_pressed is True:
            return True
        else:
            return False
