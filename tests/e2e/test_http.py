import json
from re import match
from subprocess import run

import aiohttp
import pytest

from further_link import __version__

from . import STATUS_URL, VERSION_URL


@pytest.mark.asyncio
async def test_status():
    async with aiohttp.ClientSession() as session:
        async with session.get(STATUS_URL) as response:
            assert response.status == 200
            assert await response.text() == "OK"


@pytest.mark.asyncio
async def test_version():
    async with aiohttp.ClientSession() as session:
        async with session.get(VERSION_URL) as response:
            assert response.status == 200
            body = await response.text()
            assert json.loads(body).get("version") == __version__
            assert match(r"\d+.\d+.\d+.*", __version__)


@pytest.mark.asyncio
async def test_apt_version():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{VERSION_URL}/apt/python3") as response:
            assert response.status == 200
            body = await response.text()
            try:
                run("apt")  # if apt is available, response should be useful
                assert json.loads(body).get("version").startswith("3")
            except FileNotFoundError:
                assert json.loads(body).get("version") is None
