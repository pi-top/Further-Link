from importlib.metadata import version

__version__ = "N/A"
try:
    __version__ = version("further_link")
except Exception:
    pass
