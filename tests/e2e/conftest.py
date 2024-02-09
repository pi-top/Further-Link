import urllib.parse

import pytest
from aioresponses import aioresponses as aioresponses_mock

from further_link.__main__ import create_web_app

from . import RUN_PATH


@pytest.fixture
def loop(event_loop):
    return event_loop


@pytest.fixture()
async def http_client(aiohttp_client):
    client = await aiohttp_client(await create_web_app())
    yield client
    await client.close()


@pytest.fixture()
async def run_ws_client(aiohttp_client):
    wclient = await aiohttp_client(await create_web_app())
    async with wclient.ws_connect(RUN_PATH, receive_timeout=0.1) as client:
        yield client


run_ws_client2 = run_ws_client


@pytest.fixture()
async def run_ws_client_query(aiohttp_client, query_params):
    url = RUN_PATH + "?" + urllib.parse.urlencode(query_params)
    client = await aiohttp_client(await create_web_app())
    async with client.ws_connect(url, receive_timeout=0.1) as client:
        yield client


@pytest.fixture()
def aioresponses():
    with aioresponses_mock(passthrough=["http://127.0.0.1"]) as a:
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
