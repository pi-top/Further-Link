import os
import pytest
import aiohttp
import aiofiles
import filetype
import aresponses

from server import run_async
from src.message import create_message, parse_message
from shutil import copy, rmtree
from datetime import datetime
from test.data import directory

BASE_URI = 'ws://0.0.0.0:8028'
WS_URI = BASE_URI + '/run-py'
STATUS_URI = BASE_URI + '/status'
WORKING_DIRECTORY = "{}/test/work_dir".format(os.getcwd())

os.environ['FURTHER_LINK_PORT'] = '8028'
os.environ['FURTHER_LINK_NOSSL'] = 'true'
os.environ['FURTHER_LINK_WORK_DIR'] = WORKING_DIRECTORY

# TODO:- mock successful image requests in upload tests


@pytest.fixture(autouse=True)
async def start_server():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    runner = await run_async()

    yield

    rmtree(WORKING_DIRECTORY)
    await runner.cleanup()


@pytest.fixture()
async def ws_client():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_URI) as client:
            yield client


@pytest.mark.asyncio
async def test_status():
    async with aiohttp.ClientSession() as session:
        async with session.get(STATUS_URI) as response:
            assert response.status == 200
            assert await response.text() == 'OK'


@pytest.mark.asyncio
async def test_bad_message(ws_client):
    start_cmd = create_message('start')
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}


@pytest.mark.asyncio
async def test_run_code_script(ws_client):
    code = 'from datetime import datetime\nprint(datetime.now().strftime("%A"))'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    day = datetime.now().strftime('%A')
    assert m_type == 'stdout'
    assert m_data == {'output': day + '\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_run_code_path(ws_client):
    copy('{}/test/test_code.py'.format(os.getcwd()),
         WORKING_DIRECTORY)

    start_cmd = create_message(
        'start', {'sourcePath': "test_code.py"})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    day = datetime.now().strftime('%A')
    assert m_type == 'stdout'
    assert m_data == {'output': day + '\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_run_code_absolute_path(ws_client):
    start_cmd = create_message(
        'start', {'sourcePath': "{}/test/test_code.py".format(os.getcwd())})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    day = datetime.now().strftime('%A')
    assert m_type == 'stdout'
    assert m_data == {'output': day + '\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_stop_early(ws_client):
    code = 'while True: pass'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': -15}


@pytest.mark.asyncio
async def test_bad_code(ws_client):
    code = 'i\'m not valid python'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    lines = m_data['output'].split('\n')
    assert lines[0].startswith('  File')
    assert lines[1] == '    i\'m not valid python'
    assert lines[2] == '                       ^'
    assert lines[3] == 'SyntaxError: EOL while scanning string literal'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 1}


@pytest.mark.asyncio
async def test_input(ws_client):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stdout'
    assert m_data == {'output': 'HUH?! SPEAK UP, SONNY!\n'}

    user_input = create_message('stdin', {'input': 'HEY GRANDMA\n'})
    await ws_client.send_str(user_input)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stdout'
    assert m_data == {'output': 'NO, NOT SINCE 1930\n'}

    user_input = create_message('stdin', {'input': 'BYE\n'})
    await ws_client.send_str(user_input)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_two_clients(ws_client):
    async with aiohttp.ClientSession() as session2:
        async with session2.ws_connect(WS_URI) as ws_client2:
            code = 'while True: pass'
            start_cmd = create_message('start', {'sourceScript': code})
            await ws_client.send_str(start_cmd)

            m_type, m_data = parse_message((await ws_client.receive()).data)
            assert m_type == 'started'

            await ws_client2.send_str(start_cmd)

            m_type, m_data = parse_message((await ws_client2.receive()).data)
            assert m_type == 'started'

            stop_cmd = create_message('stop')
            await ws_client.send_str(stop_cmd)

            m_type, m_data = parse_message((await ws_client.receive()).data)
            assert m_type == 'stopped'
            assert m_data == {'exitCode': -15}

            stop_cmd = create_message('stop')
            await ws_client2.send_str(stop_cmd)

            m_type, m_data = parse_message((await ws_client2.receive()).data)
            assert m_type == 'stopped'
            assert m_data == {'exitCode': -15}


@pytest.mark.asyncio
async def test_out_of_order_commands(ws_client):
    # send input
    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    # bad message
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # bad message
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}

    # send start
    code = 'while True: pass'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    # started
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    # send start
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    # bad message
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # stopped
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': -15}

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # bad message
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}


@pytest.mark.asyncio
async def test_discard_old_input(ws_client):
    code = 'print("hello world")'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    unterminated_input = create_message(
        'stdin', {'input': 'unterminated input'})
    await ws_client.send_str(unterminated_input)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stdout'
    assert m_data == {'output': 'hello world\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}

    code = 'print(input())'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stdout'
    assert m_data == {'output': 'hello\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': 0}


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
    # name directory something that tries to escape from working dir
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
