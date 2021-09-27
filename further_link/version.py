from os import path

HERE = path.abspath(path.dirname(__file__))

with open(f"{HERE}/version.txt", "r+") as f:
    __version__ = f.read().strip()
