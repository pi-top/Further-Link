import os
import pytest
from shutil import rmtree

from . import WORKING_DIRECTORY

os.environ['FURTHER_LINK_PORT'] = '8028'
os.environ['FURTHER_LINK_NOSSL'] = 'true'
os.environ['FURTHER_LINK_WORK_DIR'] = WORKING_DIRECTORY


@pytest.fixture(autouse=True)
def create_working_directory():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    yield
    rmtree(WORKING_DIRECTORY)
