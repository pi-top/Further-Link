from threading import Thread
import atexit
from pitopcommon.singleton import Singleton

from .ipc import start_ipc_server, ipc_send, ipc_cleanup


class KeyboardButtonsListener(metaclass=Singleton):
    def __init__(self):
        self.buttons = {}

        atexit.register(self.__clean_up)

        self.listener_thread = Thread(target=start_ipc_server,
                                      args=('keyevent', self.__on_key_event))
        self.listener_thread.start()

    def add_button(self, key, button):
        self.buttons[key] = button

    def __on_key_event(self, ipc_message):
        key, event = ipc_message.split(' ')
        button = self.buttons.get(key)
        if button:
            if event == 'keydown':
                button._on_press()
            elif event == 'keyup':
                button._on_release()

    def __clean_up(self):
        ipc_cleanup('keyevent')


class KeyboardButton:  # interface to match pitop.KeyboardButton
    def __init__(self, key):
        self.key = key
        self.pressed_method = None
        self.released_method = None
        self.__key_pressed = False

        listener = KeyboardButtonsListener()
        listener.add_button(key, self)
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
