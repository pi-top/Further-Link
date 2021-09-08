# This file acts as a local copy of some SDK functionality
#
# This is so that we can drop the SDK dependency which was causing some issues with tests

# from pitop.common.current_session_info import get_first_display
# from pitop.common.singleton import Singleton

from glob import glob
from os import environ
from subprocess import run
from typing import List, Optional


def get_current_user():
    """Returns the name of the user that invoked this function.
    Returns:
            user (str): String representing the user
    """
    if environ.get("SUDO_USER"):
        return environ.get("SUDO_USER")
    elif environ.get("USER"):
        return environ.get("USER")
    else:
        return get_user_using_first_display()


def get_list_of_displays() -> List[str]:
    display_file_prefix = "/tmp/.X11-unix/X"
    return [
        f.replace(display_file_prefix, ":")
        for f in glob(display_file_prefix + "[0-9]*")
    ]


def get_first_display() -> Optional[str]:
    displays = get_list_of_displays()
    first_display = displays[0] if len(displays) > 0 else None
    return first_display


def get_user_using_display(display_no):
    """Returns the name of the user that is currently using the defined
    display.
    Returns:
            user (str): String representing the user
    """

    user = None
    proc = run("who", timeout=5, capture_output=True)
    stdout = proc.stdout.decode("utf-8").strip()
    lines = stdout.split("\n")
    for line in lines:
        if "(%s)" % display_no in line:
            fields = line.split(" ")
            if len(fields) > 1:
                user = fields[0]
                break
    return user


def get_user_using_first_display():
    """Returns the name of the user that is currently using the first available
    display.
    This function is useful when targeting a particular active user by something that is running
    as something different to the current user, where `get_current_user()` would be incorrect.
    For example, with a system service, `get_current_user()` would return "root" (from the USER
    environment variable), where the active user (e.g. "pi") is actually wanted.
            Returns:
                    user (str): String representing the user
    """
    return get_user_using_display(get_first_display())


class Singleton(type):
    def __init__(cls, name, bases, dic):
        super(Singleton, cls).__init__(name, bases, dic)
        cls.instance = None

    def __call__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance
