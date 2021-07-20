import os
import pytest
import aiohttp
import urllib.parse

from shutil import rmtree
from aioresponses import aioresponses as aioresponses_mock

from tests import WORKING_DIRECTORY, RUN_URL, RUN_PY_URL
from server import create_app

os.environ['FURTHER_LINK_PORT'] = '8028'
os.environ['FURTHER_LINK_NOSSL'] = 'true'
os.environ['FURTHER_LINK_WORK_DIR'] = WORKING_DIRECTORY


@pytest.fixture(autouse=True)
def create_working_directory():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    yield
    rmtree(WORKING_DIRECTORY)


# @pytest.fixture(autouse=True)
# async def start_server():
#     runner = await run_async()
#     yield
#     await runner.shutdown()
#     await runner.cleanup()


@pytest.fixture
def loop(event_loop):
    return event_loop


@pytest.fixture()
async def run_py_ws_client(loop, aiohttp_client):
    url = '/run-py'
    client = await aiohttp_client(create_app())
    async with client.ws_connect(url, receive_timeout=0.1) as client:
        yield client

run_py_ws_client2 = run_py_ws_client


@pytest.fixture()
async def run_py_ws_client_query(aiohttp_client, query_params):
    url = '/run-py' + '?' + urllib.parse.urlencode(query_params)
    client = await aiohttp_client(create_app())
    async with client.ws_connect(url, receive_timeout=0.1) as client:
        yield client


@pytest.fixture()
async def run_ws_client():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            RUN_URL, receive_timeout=0.1
        ) as client:
            yield client


@pytest.fixture()
async def run_ws_client_query(query_params):
    url = RUN_URL + '?' + urllib.parse.urlencode(query_params)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, receive_timeout=0.1) as client:
            yield client


@pytest.fixture
def aioresponses():
    with aioresponses_mock(passthrough=['http://0.0.0.0']) as a:
        yield a
