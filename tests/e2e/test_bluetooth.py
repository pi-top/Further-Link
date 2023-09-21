import asyncio
import json
import os
from pathlib import Path

import aiofiles
import pytest

from further_link.util.bluetooth.gatt import (
    PT_APT_VERSION_CHARACTERISTIC_UUID,
    PT_RUN_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_UPLOAD_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.messages import ChunkedMessage
from further_link.util.bluetooth.utils import bytearray_to_dict
from further_link.util.upload import get_bucket_cache_path, get_directory_path
from further_link.util.user_config import (
    default_user,
    get_miniscreen_projects_directory,
)

from ..dirs import WORKING_DIRECTORY
from .test_data.upload_data import directory, directory_with_project


async def send_long_message(
    client, characteristic, message, assert_characteristic_value=True
):
    chunked_message = ChunkedMessage.from_long_message(json.dumps(message))

    for i in range(chunked_message.total_chunks):
        chunk = chunked_message.chunk(i)

        # send chunk to server
        client.server.write(characteristic, chunk)
        await asyncio.sleep(0.3)
        if assert_characteristic_value:
            # read and confirm it's the same message as the one sent
            assert client.read_value(characteristic.uuid) == chunk

    await asyncio.sleep(0.3)


async def assert_uploaded(upload_data, has_miniscreen_project):
    directory_path = get_directory_path(WORKING_DIRECTORY, upload_data["name"])
    projects_base_path = get_miniscreen_projects_directory(
        upload_data["name"], None, upload_data["username"]
    )

    for alias_name, file_info in upload_data["files"].items():
        alias_path = os.path.join(directory_path, alias_name)

        assert os.path.isfile(alias_path)

        if file_info["type"] == "url":
            content = file_info["content"]
            bucket_name = content["bucketName"]
            file_name = content["fileName"]
            bucket_cache_path = get_bucket_cache_path(WORKING_DIRECTORY, bucket_name)
            file_path = os.path.join(bucket_cache_path, file_name)
            assert os.path.isfile(file_path)
            if has_miniscreen_project:
                path = Path(f"{projects_base_path}/{alias_name}")
                assert path.is_file()
                assert path.owner() == default_user()
            else:
                assert not os.path.isfile(f"{projects_base_path}/{alias_name}")

        elif file_info["type"] == "text":
            async with aiofiles.open(alias_path) as file:
                content = await file.read()
                assert content == file_info["content"]["text"]

            if has_miniscreen_project:
                path = Path(f"{projects_base_path}/{alias_name}")
                assert path.is_file()
                assert path.owner() == default_user()
            else:
                assert not os.path.isfile(f"{projects_base_path}/{alias_name}")


def test_status_characteristic_read(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_STATUS_CHARACTERISTIC_UUID
    )
    assert bluetooth_client.server.read(char) == b"OK"


def test_version_characteristic_read(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_VERSION_CHARACTERISTIC_UUID
    )
    assert bluetooth_client.server.read(char) == b'{"version": "0.0.1.dev1"}'


async def test_apt_version(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_APT_VERSION_CHARACTERISTIC_UUID
    )
    bluetooth_client.server.write(char, b"python3")

    await asyncio.sleep(0.5)

    resp = bytearray_to_dict(bluetooth_client.read_value(char.uuid))

    assert "version" in resp
    assert resp["version"].startswith("3")


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )

    await send_long_message(bluetooth_client, char, directory)
    await assert_uploaded(directory, has_miniscreen_project=False)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload_with_miniscreen_project(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )

    await send_long_message(bluetooth_client, char, directory_with_project)
    await assert_uploaded(directory_with_project, has_miniscreen_project=True)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload_wrong_message(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )
    bluetooth_client.server.write(char, b"")

    await asyncio.sleep(0.5)

    resp = bluetooth_client.read_value(char.uuid)
    assert resp == b"Error: invalid format"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload_existing_directory(bluetooth_client):
    existing_directory = directory.copy()
    existing_directory["name"] = "existing_directory"
    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))

    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )

    await send_long_message(bluetooth_client, char, existing_directory)
    await assert_uploaded(existing_directory, has_miniscreen_project=False)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload_restricted_directory(bluetooth_client):
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory["name"] = "../injected"

    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )

    await send_long_message(
        bluetooth_client, char, restricted_directory, assert_characteristic_value=False
    )

    resp = bluetooth_client.read_value(char.uuid)
    assert resp == b"Error: Forbidden directory name ../injected"


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3)
async def test_upload_no_internet(aioresponses, bluetooth_client):
    aioresponses.head("https://google.com", exception=Exception("no internet"))

    char = bluetooth_client.server.get_service(PT_RUN_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_CHARACTERISTIC_UUID
    )
    await send_long_message(bluetooth_client, char, directory)

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
