import pytest
import aiohttp
import asyncio
import json
from datetime import datetime
from subprocess import run

from shutil import copy

from src.message import create_message, parse_message
from src.lib.further_link import __version__
from tests import TEST_PATH, WORKING_DIRECTORY, STATUS_URL, VERSION_URL, \
    RUN_PY_URL
from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_status():
    async with aiohttp.ClientSession() as session:
        async with session.get(STATUS_URL) as response:
            assert response.status == 200
            assert await response.text() == 'OK'


@pytest.mark.asyncio
async def test_version():
    async with aiohttp.ClientSession() as session:
        async with session.get(VERSION_URL) as response:
            assert response.status == 200
            body = await response.text()
            assert json.loads(body).get('version') == __version__


@pytest.mark.asyncio
async def test_apt_version():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{VERSION_URL}/apt/python3') as response:
            assert response.status == 200
            body = await response.text()
            try:
                run('apt')  # if apt is available, response should be useful
                assert json.loads(body).get('version').startswith('3')
            except FileNotFoundError:
                assert json.loads(body).get('version') is None


@pytest.mark.asyncio
async def test_bad_message(ws_client):
    start_cmd = create_message('start')
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'error', 'message', 'Bad message')


@pytest.mark.asyncio
async def test_run_code_script(ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    day = datetime.now().strftime('%A')
    await wait_for_data(ws_client, 'stdout', 'output', day + '\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_run_code_script_with_directory(ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message('start', {
        'sourceScript': code,
        'directoryName': "my-dirname"
    })
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    day = datetime.now().strftime('%A')
    await wait_for_data(ws_client, 'stdout', 'output', day + '\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_run_code_relative_path(ws_client):
    copy('{}/test_data/print_date.py'.format(TEST_PATH), WORKING_DIRECTORY)

    start_cmd = create_message('start', {'sourcePath': "print_date.py"})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    day = datetime.now().strftime('%A')
    await wait_for_data(ws_client, 'stdout', 'output', day + '\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_run_code_absolute_path(ws_client):
    start_cmd = create_message('start', {
        'sourcePath': "{}/test_data/print_date.py".format(TEST_PATH)
    })
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    day = datetime.now().strftime('%A')
    await wait_for_data(ws_client, 'stdout', 'output', day + '\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
@pytest.mark.parametrize('query_params', [{'user': 'root'}])
@pytest.mark.skip(reason="Won't work in CI due to old sudo version")
async def test_run_as_user(ws_client_query):
    # This test assumes non-root user with nopasswd sudo access...
    code = 'import getpass\nprint(getpass.getuser())'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client_query.send_str(start_cmd)

    await receive_data(ws_client_query, 'started')

    await wait_for_data(ws_client_query, 'stdout', 'output', 'root\n', 100)

    await wait_for_data(ws_client_query, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_stop_early(ws_client):
    code = 'while True: pass'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    await wait_for_data(ws_client, 'stopped', 'exitCode', -15, 100)


@pytest.mark.asyncio
async def test_bad_code(ws_client):
    code = 'i\'m not valid python'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    await asyncio.sleep(0.1)  # wait for data
    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    lines = m_data['output'].split('\n')
    assert lines[0].startswith('  File')
    assert lines[1] == '    i\'m not valid python'
    assert lines[2] == '                       ^'
    assert lines[3] == 'SyntaxError: EOL while scanning string literal'

    await wait_for_data(ws_client, 'stopped', 'exitCode', 1, 100)


@pytest.mark.asyncio
async def test_input(ws_client):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    await wait_for_data(ws_client, 'stdout', 'output', 'HUH?! SPEAK UP, SONNY!\n', 100)

    user_input = create_message('stdin', {'input': 'HEY GRANDMA\n'})
    await ws_client.send_str(user_input)

    await wait_for_data(ws_client, 'stdout', 'output', 'NO, NOT SINCE 1930\n', 100)

    user_input = create_message('stdin', {'input': 'BYE\n'})
    await ws_client.send_str(user_input)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
@pytest.mark.parametrize('query_params', [{'pty': '1'}])
async def test_input_pty(ws_client_query):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client_query.send_str(start_cmd)

    await receive_data(ws_client_query, 'started')

    user_input = create_message('stdin', {'input': 'hello\r'})
    await ws_client_query.send_str(user_input)

    await wait_for_data(ws_client_query, 'stdout', 'output',
                        'hello\r\nHUH?! SPEAK UP, SONNY!\r\n', 100)

    user_input = create_message('stdin', {'input': 'HEY GRANDMA\r'})
    await ws_client_query.send_str(user_input)

    await wait_for_data(ws_client_query, 'stdout', 'output',
                        'HEY GRANDMA\r\nNO, NOT SINCE 1930\r\n', 100)

    user_input = create_message('stdin', {'input': 'BYE\r'})
    await ws_client_query.send_str(user_input)

    await wait_for_data(ws_client_query, 'stdout', 'output', 'BYE\r\n', 100)

    await wait_for_data(ws_client_query, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_two_clients(ws_client):
    async with aiohttp.ClientSession() as session2:
        async with session2.ws_connect(RUN_PY_URL) as ws_client2:
            code = 'while True: pass'
            start_cmd = create_message('start', {'sourceScript': code})
            await ws_client.send_str(start_cmd)

            await receive_data(ws_client, 'started')

            await ws_client2.send_str(start_cmd)

            await receive_data(ws_client2, 'started')

            stop_cmd = create_message('stop')
            await ws_client.send_str(stop_cmd)

            await wait_for_data(ws_client, 'stopped', 'exitCode', -15, 100)

            stop_cmd = create_message('stop')
            await ws_client2.send_str(stop_cmd)

            await wait_for_data(ws_client2, 'stopped', 'exitCode', -15, 100)


@pytest.mark.asyncio
async def test_out_of_order_commands(ws_client):
    # send input
    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    # bad message
    await receive_data(ws_client, 'error', 'message', 'Bad message')

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(ws_client, 'error', 'message', 'Bad message')

    # send start
    code = 'while True: pass'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    # started
    await receive_data(ws_client, 'started')

    # send start
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    # bad message
    await receive_data(ws_client, 'error', 'message', 'Bad message')

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # stopped
    await wait_for_data(ws_client, 'stopped', 'exitCode', -15, 100)

    # send stop
    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(ws_client, 'error', 'message', 'Bad message')


@pytest.mark.asyncio
async def test_discard_old_input(ws_client):
    code = 'print("hello world")'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    unterminated_input = create_message(
        'stdin', {'input': 'unterminated input'})
    await ws_client.send_str(unterminated_input)

    await wait_for_data(ws_client, 'stdout', 'output', 'hello world\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)

    code = 'print(input())'
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    user_input = create_message('stdin', {'input': 'hello\n'})
    await ws_client.send_str(user_input)

    await wait_for_data(ws_client, 'stdout', 'output', 'hello\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_use_lib(ws_client):
    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await receive_data(ws_client, 'started')

    await wait_for_data(ws_client, 'stdout', 'output', f'{__version__}\n', 100)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)

jpeg_pixel_b64 = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z'


@pytest.mark.asyncio
async def test_send_image_pil(ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await wait_for_data(ws_client, 'started')

    await wait_for_data(ws_client, 'video', 'output', jpeg_pixel_b64)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_send_image_opencv(ws_client):
    code = """\
from numpy import array
from further_link import send_image
from PIL.Image import effect_noise
send_image(array(effect_noise((1, 1), 0)))
"""
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    await wait_for_data(ws_client, 'started')

    await wait_for_data(ws_client, 'video', 'output', jpeg_pixel_b64)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)


@pytest.mark.asyncio
async def test_send_image_with_directory(ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message('start', {
        'sourceScript': code,
        'directoryName': "my-dirname"
    })
    await ws_client.send_str(start_cmd)

    await wait_for_data(ws_client, 'started')

    await wait_for_data(ws_client, 'video', 'output', jpeg_pixel_b64)

    await wait_for_data(ws_client, 'stopped', 'exitCode', 0, 100)
