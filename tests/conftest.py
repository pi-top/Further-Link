import os
import pytest
import aiohttp

from shutil import rmtree

from tests import WORKING_DIRECTORY, RUN_PY_URL
from server import run_async

os.environ['FURTHER_LINK_PORT'] = '8028'
os.environ['FURTHER_LINK_NOSSL'] = 'true'
os.environ['FURTHER_LINK_WORK_DIR'] = WORKING_DIRECTORY


@pytest.fixture(autouse=True)
def create_working_directory():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    yield
    rmtree(WORKING_DIRECTORY)


@pytest.fixture(autouse=True)
async def start_server():
    runner = await run_async()
    yield
    await runner.cleanup()


@pytest.fixture()
async def ws_client():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(RUN_PY_URL) as client:
            yield client
