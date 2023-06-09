import json
import os
from pathlib import Path

import aiofiles
import pytest

from further_link.util.upload import get_bucket_cache_path, get_directory_path
from further_link.util.user_config import (
    default_user,
    get_miniscreen_projects_directory,
)

from ..dirs import WORKING_DIRECTORY
from . import UPLOAD_PATH
from .test_data.upload_data import directory, directory_with_project


@pytest.mark.asyncio
async def test_upload_empty_directory(http_client):
    response = await http_client.post(UPLOAD_PATH, data=b"{}")
    assert response.status == 400
    body = await response.text()
    assert body == "400: Bad Request"


@pytest.mark.asyncio
async def test_upload(http_client):
    upload_data = json.dumps(directory).encode()
    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 200
    body = await response.text()
    assert json.loads(body).get("success")

    directory_path = get_directory_path(WORKING_DIRECTORY, directory["name"])
    projects_base_path = get_miniscreen_projects_directory(
        directory["name"], None, directory["username"]
    )

    for alias_name, file_info in directory["files"].items():
        alias_path = os.path.join(directory_path, alias_name)

        assert os.path.isfile(alias_path)

        if file_info["type"] == "url":
            content = file_info["content"]
            bucket_name = content["bucketName"]
            file_name = content["fileName"]
            bucket_cache_path = get_bucket_cache_path(WORKING_DIRECTORY, bucket_name)
            file_path = os.path.join(bucket_cache_path, file_name)
            assert os.path.isfile(file_path)

            assert not os.path.isfile(f"{projects_base_path}/{alias_name}")

        elif file_info["type"] == "text":
            async with aiofiles.open(alias_path) as file:
                content = await file.read()
                assert content == file_info["content"]["text"]

            assert not os.path.isfile(f"{projects_base_path}/{alias_name}")


@pytest.mark.asyncio
async def test_upload_with_miniscreen_project(http_client):
    upload_data = json.dumps(directory_with_project).encode()
    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 200
    body = await response.text()
    assert json.loads(body).get("success")

    directory_path = get_directory_path(
        WORKING_DIRECTORY, directory_with_project["name"]
    )
    projects_base_path = get_miniscreen_projects_directory(
        directory_with_project["name"], None, directory_with_project["username"]
    )

    for alias_name, file_info in directory_with_project["files"].items():
        alias_path = os.path.join(directory_path, alias_name)

        assert os.path.isfile(alias_path)

        if file_info["type"] == "url":
            content = file_info["content"]
            bucket_name = content["bucketName"]
            file_name = content["fileName"]
            bucket_cache_path = get_bucket_cache_path(WORKING_DIRECTORY, bucket_name)
            file_path = os.path.join(bucket_cache_path, file_name)
            assert os.path.isfile(file_path)

            path = Path(f"{projects_base_path}/{alias_name}")
            assert path.is_file()
            assert path.owner() == default_user()

        elif file_info["type"] == "text":
            async with aiofiles.open(alias_path) as file:
                content = await file.read()
                assert content == file_info["content"]["text"]

            path = Path(f"{projects_base_path}/{alias_name}")
            assert path.is_file()
            assert path.owner() == default_user()


@pytest.mark.asyncio
async def test_upload_bad_file(http_client, aioresponses):
    upload_data = json.dumps(directory).encode()
    aioresponses.head("https://google.com", status=200)
    aioresponses.get("https://placekitten.com/50/50", status=500)

    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 500
    body = await response.text()
    assert body == "500: Internal Server Error"


@pytest.mark.asyncio
async def test_upload_existing_directory(http_client):
    existing_directory = directory.copy()
    existing_directory["name"] = "existing_directory"
    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))
    upload_data = json.dumps(existing_directory).encode()

    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 200
    body = await response.text()
    assert json.loads(body).get("success")


@pytest.mark.asyncio
async def test_upload_restricted_directory(http_client):
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory["name"] = "../injected"
    upload_data = json.dumps(restricted_directory).encode()

    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 500
    body = await response.text()
    assert body == "500: Internal Server Error"


@pytest.mark.asyncio
async def test_upload_no_internet(http_client, aioresponses):
    aioresponses.head("https://google.com", exception=Exception("no internet"))

    upload_data = json.dumps(directory).encode()
    response = await http_client.post(UPLOAD_PATH, data=upload_data)
    assert response.status == 200
    body = await response.text()
    assert json.loads(body).get("success")

    directory_path = get_directory_path(WORKING_DIRECTORY, directory["name"])

    for alias_name, file_info in directory["files"].items():
        alias_path = os.path.join(directory_path, alias_name)

        if file_info["type"] == "url":
            content = file_info["content"]
            bucket_name = content["bucketName"]
            file_name = content["fileName"]
            bucket_cache_path = get_bucket_cache_path(WORKING_DIRECTORY, bucket_name)
            file_path = os.path.join(bucket_cache_path, file_name)

            # url files don't get created
            assert not os.path.isfile(alias_path)
            assert not os.path.isfile(file_path)

        elif file_info["type"] == "text":
            assert os.path.isfile(alias_path)

            async with aiofiles.open(alias_path) as file:
                content = await file.read()
                assert content == file_info["content"]["text"]
