import os
from shutil import rmtree

import pytest

from .dirs import WORKING_DIRECTORY

os.environ["FURTHER_LINK_PORT"] = "8028"
os.environ["FURTHER_LINK_NOSSL"] = "true"
os.environ["FURTHER_LINK_WORK_DIR"] = WORKING_DIRECTORY


@pytest.fixture(autouse=True)
def create_working_directory():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    yield
    rmtree(WORKING_DIRECTORY)


@pytest.fixture(autouse=True)
def clear_loggers():
    # this probably isn't the best solution to this problem
    # https://github.com/pytest-dev/pytest/issues/5502#issuecomment-647157873
    """Remove handlers from all loggers"""
    import logging

    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for logger in loggers:
        handlers = getattr(logger, "handlers", [])
        for handler in handlers:
            logger.removeHandler(handler)
