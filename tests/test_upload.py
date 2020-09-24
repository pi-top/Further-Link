import pytest
import os

from tests import WORKING_DIRECTORY
from src.message import create_message, parse_message
from .test_data.upload_data import directory


@pytest.mark.asyncio
async def test_upload(ws_client):
    upload_cmd = create_message('upload', {'directory': directory})
    await ws_client.send_str(upload_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'uploaded'

    for aliasName, file_info in directory["files"].items():
        alias_path = "{}/{}/{}".format(WORKING_DIRECTORY,
                                       directory["name"], aliasName)

        assert os.path.isfile(alias_path)
        content = file_info["content"]
        bucketName = content['bucketName']
        fileName = content['fileName']
        file_path = "{}/{}/{}".format(WORKING_DIRECTORY,
                                      bucketName, fileName)
        assert os.path.isfile(file_path)


# @pytest.mark.asyncio
# async def test_upload_run_directory(ws_client):
#     upload_cmd = create_message('upload', {'directory': directory})
#     await ws_client.send_str(upload_cmd)

#     m_type, m_data = parse_message((await ws_client.receive()).data)
#     assert m_type == 'uploaded'

#     start_cmd = create_message(
#         'start', {'sourcePath': "{}/test.py".format(directory['name'])})
#     await ws_client.send_str(start_cmd)

#     m_type, m_data = parse_message((await ws_client.receive()).data)
#     assert m_type == 'started'

#     m_type, m_data = parse_message((await ws_client.receive()).data)
#     assert m_type == 'stdout'
#     assert m_data == {'output': 'lib called\n'}

#     m_type, m_data = parse_message((await ws_client.receive()).data)
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_upload_bad_file(ws_client, aresponses):
    aresponses.add('https://placekitten.com/50/50', '/', 'GET',
                   aresponses.Response(text='error', status=500))

    upload_cmd = create_message('upload', {'directory': directory})
    await ws_client.send_str(upload_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad upload'}


@pytest.mark.asyncio
async def test_upload_existing_directory(ws_client):
    existing_directory = directory.copy()
    existing_directory['name'] = 'existing_directory'

    os.mkdir("{}/existing_directory".format(WORKING_DIRECTORY))

    upload_cmd = create_message('upload', {'directory': existing_directory})
    await ws_client.send_str(upload_cmd)

    m_type, _ = parse_message((await ws_client.receive()).data)
    assert m_type == 'uploaded'


@pytest.mark.asyncio
async def test_upload_restricted_directory(ws_client):
    # name directory something that tries to escape from working dir
    restricted_directory = directory.copy()
    restricted_directory['name'] = '../injected'

    upload_cmd = create_message('upload', {'directory': restricted_directory})
    await ws_client.send_str(upload_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad upload'}


@pytest.mark.asyncio
async def test_upload_empty_directory(ws_client):
    upload_cmd = create_message('upload', {'directory': {}})
    await ws_client.send_str(upload_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}
