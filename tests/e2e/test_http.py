import json
from re import match
from subprocess import run

import pytest

from further_link import __version__

from . import STATUS_PATH, VERSION_PATH


@pytest.mark.asyncio
async def test_status(http_client):
    response = await http_client.get(STATUS_PATH)
    assert response.status == 200
    assert response.headers["Access-Control-Allow-Private-Network"] == "true"
    assert await response.text() == "OK"


@pytest.mark.asyncio
async def test_version(http_client):
    response = await http_client.get(VERSION_PATH)
    assert response.status == 200
    body = await response.text()
    assert json.loads(body).get("version") == __version__
    assert match(r"\d+.\d+.\d+.*", __version__)


@pytest.mark.asyncio
async def test_apt_version(http_client):
    response = await http_client.get(f"{VERSION_PATH}/apt/python3")
    assert response.status == 200
    body = await response.text()
    try:
        run("apt")  # if apt is available, response should be useful
        assert json.loads(body).get("version").startswith("3")
    except FileNotFoundError:
        assert json.loads(body).get("version") is None
