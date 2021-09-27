import urllib.parse

import aiohttp
import pytest
from aioresponses import aioresponses as aioresponses_mock

from further_link.__main__ import run_async

from . import RUN_PY_URL, RUN_URL


@pytest.fixture(autouse=True)
async def start_server():
    runner = await run_async()
    yield
    await runner.cleanup()


@pytest.fixture()
async def run_py_ws_client():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(RUN_PY_URL, receive_timeout=0.1) as client:
            yield client


@pytest.fixture()
async def run_py_ws_client_query(query_params):
    url = RUN_PY_URL + "?" + urllib.parse.urlencode(query_params)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, receive_timeout=0.1) as client:
            yield client


@pytest.fixture()
async def run_ws_client():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(RUN_URL, receive_timeout=0.1) as client:
            yield client


@pytest.fixture()
async def run_ws_client_query(query_params):
    url = RUN_URL + "?" + urllib.parse.urlencode(query_params)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, receive_timeout=0.1) as client:
            yield client


@pytest.fixture()
def aioresponses():
    with aioresponses_mock(passthrough=["http://0.0.0.0"]) as a:
        yield a


@pytest.fixture(autouse=True)
def clear_loggers():
    # https://github.com/pytest-dev/pytest/issues/5502#issuecomment-647157873
    """Remove handlers from all loggers"""
    import logging

    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for logger in loggers:
        handlers = getattr(logger, "handlers", [])
        for handler in handlers:
            logger.removeHandler(handler)
