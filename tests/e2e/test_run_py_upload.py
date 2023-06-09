import asyncio
import os

import aiofiles
import pytest

from further_link.util.message import create_message, parse_message
from further_link.util.upload import get_bucket_cache_path, get_directory_path

from ..dirs import WORKING_DIRECTORY
from .helpers import receive_data, wait_for_data
from .test_data.upload_data import directory


@pytest.mark.asyncio
async def test_upload(run_py_ws_client):
    upload_cmd = create_message("upload", {"directory": directory})
    await run_py_ws_client.send_str(upload_cmd)

    await wait_for_data(run_py_ws_client, "uploaded")

    directory_path = get_directory_path(WORKING_DIRECTORY, directory["name"])

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

        elif file_info["type"] == "url":
            async with aiofiles.open(file_path) as file:
                content = await file.read()
                assert content == file_info["content"]["text"]


@pytest.mark.asyncio
async def test_upload_read_file(run_py_ws_client):
    upload_cmd = create_message("upload", {"directory": directory})
    await run_py_ws_client.send_str(upload_cmd)

    await wait_for_data(run_py_ws_client, "uploaded")

    code = """\
import os
with open(os.path.dirname(__file__) + '/cereal.csv', 'r') as f:
    print(f.read(1000))
"""
    start_cmd = create_message(
        "start", {"sourceScript": code, "directoryName": directory["name"]}
    )
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    await asyncio.sleep(0.2)  # wait for data
    message = await run_py_ws_client.receive()
    m_type, m_data, m_process = parse_message(message.data)
    assert m_type == "stdout"
    assert m_data["output"][788:796] == "Cheerios"

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_upload_import_script(run_py_ws_client):
    upload_cmd = create_message("upload", {"directory": directory})
    await run_py_ws_client.send_str(upload_cmd)

    await wait_for_data(run_py_ws_client, "uploaded")

    code = """\
from some_lib import call_some_lib
print(call_some_lib())
"""
    start_cmd = create_message(
        "start", {"sourceScript": code, "directoryName": directory["name"]}
    )
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "stdout", "output", "some lib called\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_upload_bad_file(run_py_ws_client, aioresponses):
    aioresponses.head("https://google.com", status=200)
    aioresponses.add("https://placekitten.com/50/50", status=500)

    upload_cmd = create_message("upload", {"directory": directory})
    await run_py_ws_client.send_str(upload_cmd)

    await receive_data(run_py_ws_client, "error", "message", "Bad upload")


@pytest.mark.asyncio
async def test_upload_existing_directory(run_py_ws_client):
    existing_directory = directory.copy()
    existing_directory["name"] = "existing_directory"

    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))

    upload_cmd = create_message("upload", {"directory": existing_directory})
    await run_py_ws_client.send_str(upload_cmd)

    await wait_for_data(run_py_ws_client, "uploaded")


@pytest.mark.asyncio
async def test_upload_restricted_directory(run_py_ws_client):
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory["name"] = "../injected"

    upload_cmd = create_message("upload", {"directory": restricted_directory})
    await run_py_ws_client.send_str(upload_cmd)

    await receive_data(run_py_ws_client, "error", "message", "Bad upload")


@pytest.mark.asyncio
async def test_upload_empty_directory(run_py_ws_client):
    upload_cmd = create_message("upload", {"directory": {}})
    await run_py_ws_client.send_str(upload_cmd)

    await receive_data(run_py_ws_client, "error", "message", "Bad message")
