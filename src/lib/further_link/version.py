# In a deb or docker build this file should be replaced by a simple __version__ = 'X.X.X'

from os import path
from re import search

__version__ = 'Undefined'

changelog = path.abspath(path.join(__file__, '../../../../debian/changelog'))
version_regex = r'pt-further-link \((.*?)\).*'

with open(changelog) as f:
    first_line = f.readline()
    __version__ = search(version_regex, first_line).group(1)
