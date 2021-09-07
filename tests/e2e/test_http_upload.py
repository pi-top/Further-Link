import json
import os

import aiofiles
import aiohttp
import pytest
from src.upload import get_bucket_cache_path, get_directory_path

from ..dirs import WORKING_DIRECTORY
from . import UPLOAD_URL
from .test_data.upload_data import directory


@pytest.mark.asyncio
async def test_upload_empty_directory():
    async with aiohttp.ClientSession() as session:
        async with session.post(UPLOAD_URL, data=b"{}") as response:
            assert response.status == 400
            body = await response.text()
            assert body == "400: Bad Request"


@pytest.mark.asyncio
async def test_upload():
    upload_data = json.dumps(directory).encode()
    async with aiohttp.ClientSession() as session:
        async with session.post(UPLOAD_URL, data=upload_data) as response:
            assert response.status == 200
            body = await response.text()
            assert body == "OK"

            directory_path = get_directory_path(WORKING_DIRECTORY, directory["name"])

            for alias_name, file_info in directory["files"].items():
                alias_path = os.path.join(directory_path, alias_name)

                assert os.path.isfile(alias_path)

                if file_info["type"] == "url":
                    content = file_info["content"]
                    bucket_name = content["bucketName"]
                    file_name = content["fileName"]
                    bucket_cache_path = get_bucket_cache_path(
                        WORKING_DIRECTORY, bucket_name
                    )
                    file_path = os.path.join(bucket_cache_path, file_name)
                    assert os.path.isfile(file_path)

                elif file_info["type"] == "url":
                    async with aiofiles.open(file_path) as file:
                        content = await file.read()
                        assert content == file_info["content"]["text"]


@pytest.mark.asyncio
async def test_upload_bad_file(aioresponses):
    upload_data = json.dumps(directory).encode()
    aioresponses.get("https://placekitten.com/50/50", status=500)

    async with aiohttp.ClientSession() as session:
        async with session.post(UPLOAD_URL, data=upload_data) as response:
            assert response.status == 500
            body = await response.text()
            assert body == "500: Internal Server Error"


@pytest.mark.asyncio
async def test_upload_existing_directory():
    existing_directory = directory.copy()
    existing_directory["name"] = "existing_directory"
    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))
    upload_data = json.dumps(existing_directory).encode()

    async with aiohttp.ClientSession() as session:
        async with session.post(UPLOAD_URL, data=upload_data) as response:
            assert response.status == 200
            body = await response.text()
            assert body == "OK"


@pytest.mark.asyncio
async def test_upload_restricted_directory():
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory["name"] = "../injected"
    upload_data = json.dumps(restricted_directory).encode()

    async with aiohttp.ClientSession() as session:
        async with session.post(UPLOAD_URL, data=upload_data) as response:
            assert response.status == 500
            body = await response.text()
            assert body == "500: Internal Server Error"
