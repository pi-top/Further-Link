import asyncio
import json
import os
from pathlib import Path

import aiofiles
import pytest

from further_link.util.bluetooth.gatt import (
    PT_SERVICE_UUID,
    PT_UPLOAD_READ_CHARACTERISTIC_UUID,
    PT_UPLOAD_WRITE_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.messages import ChunkedMessage
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
    if not isinstance(message, str):
        message = json.dumps(message)
    chunked_message = ChunkedMessage.from_long_message(message)

    for i in range(chunked_message.total_chunks):
        chunk = chunked_message.chunk(i)

        # send chunk to server
        client.server.write(characteristic, chunk)

        # read characteristic value and confirm it's the same message as the one sent
        if assert_characteristic_value:
            assert client.read_value(characteristic.uuid) == chunk


async def wait_until_value_is(client, characteristic_uuid, value, timeout=5):
    elapsed = 0.0
    delta_t = 0.1
    while client.read_value(characteristic_uuid) != value and elapsed < timeout:
        await asyncio.sleep(delta_t)
        elapsed += delta_t

    if elapsed >= timeout:
        raise TimeoutError(
            f"Timed out waiting for {value} on characteristic {characteristic_uuid}; read '{client.read_value(characteristic_uuid)}'"
        )


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


@pytest.mark.asyncio
async def test_upload(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # send message in chunks
    await send_long_message(bluetooth_client, char, directory)

    # wait until callback is executed and check status characteristic
    await wait_until_value_is(
        bluetooth_client,
        PT_UPLOAD_READ_CHARACTERISTIC_UUID,
        b'{"success": true, "fetched_urls": true}',
    )

    # assert files were created
    await assert_uploaded(directory, has_miniscreen_project=False)


@pytest.mark.asyncio
async def test_upload_with_miniscreen_project(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # send message in chunks
    await send_long_message(bluetooth_client, char, directory_with_project)

    # wait until callback is executed and check status
    await wait_until_value_is(
        bluetooth_client,
        PT_UPLOAD_READ_CHARACTERISTIC_UUID,
        b'{"success": true, "fetched_urls": true}',
    )

    # assert files were created
    await assert_uploaded(directory_with_project, has_miniscreen_project=True)


@pytest.mark.asyncio
async def test_upload_invalid_message(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # write an invalid value to characteristic
    bluetooth_client.server.write(char, b"")

    # wait until error is reported on status characteristic
    await wait_until_value_is(
        bluetooth_client, PT_UPLOAD_READ_CHARACTERISTIC_UUID, b"Error: Invalid format"
    )


@pytest.mark.asyncio
async def test_upload_existing_directory(bluetooth_client):
    existing_directory = directory.copy()
    existing_directory["name"] = "existing_directory"
    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))

    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # send message in chunks
    await send_long_message(bluetooth_client, char, existing_directory)

    # wait until callback is executed and check status
    await wait_until_value_is(
        bluetooth_client,
        PT_UPLOAD_READ_CHARACTERISTIC_UUID,
        b'{"success": true, "fetched_urls": true}',
    )

    # assert files were created
    await assert_uploaded(existing_directory, has_miniscreen_project=False)


@pytest.mark.asyncio
async def test_upload_restricted_directory(bluetooth_client):
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory["name"] = "../injected"

    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # send message in chunks
    await send_long_message(bluetooth_client, char, restricted_directory)

    # wait until callback is executed and check status
    await wait_until_value_is(
        bluetooth_client,
        PT_UPLOAD_READ_CHARACTERISTIC_UUID,
        b"Error: Forbidden directory name ../injected",
    )


@pytest.mark.asyncio
async def test_upload_no_internet(aioresponses, bluetooth_client):
    aioresponses.head("https://google.com", exception=Exception("no internet"))

    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID
    )

    # send message in chunks
    await send_long_message(bluetooth_client, char, directory)

    # wait until callback is executed and check status
    await wait_until_value_is(
        bluetooth_client,
        PT_UPLOAD_READ_CHARACTERISTIC_UUID,
        b'{"success": true, "fetched_urls": false}',
    )

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
