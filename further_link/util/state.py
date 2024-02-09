from configparser import ConfigParser
from os import environ
from pathlib import Path
from threading import Lock

STATE_FILE_DIR = "/var/lib" if environ.get("TESTING", "") != "1" else "/tmp"
STATE_FILE_PATH = f"{STATE_FILE_DIR}/further-link/state.cfg"
config_parser = ConfigParser()

path = Path(STATE_FILE_PATH)
lock = Lock()

if not path.exists():
    Path(path.parent).mkdir(parents=True, exist_ok=True)
    path.touch()

config_parser.read(STATE_FILE_PATH)


def get(section: str, key: str, fallback=None):
    with lock:
        val = fallback
        try:
            val = config_parser.get(section, key)
        except Exception:
            if fallback is None:
                raise
        return val


def set(section: str, key: str, value):
    with lock:
        try:
            if not config_parser.has_section(section):
                config_parser.add_section(section)
            config_parser.set(section, key, value)
        except Exception:
            raise
        __save()


def remove(section: str, key: str = ""):
    with lock:
        try:
            if key and config_parser.has_option(section, key):
                config_parser.remove_option(section, key)
            elif len(key) == 0 and config_parser.has_section(section):
                config_parser.remove_section(section)
        except Exception:
            raise
        __save()


def __save():
    with open(STATE_FILE_PATH, "w") as f:
        config_parser.write(f)
