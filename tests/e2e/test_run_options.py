import pytest
from datetime import datetime

from shutil import copy

from src.util.message import create_message
from tests import WORKING_DIRECTORY
from . import E2E_PATH
from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_run_code_script_with_directory(run_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message('start', {
        'runner': 'python3',
        'code': code,
        'directoryName': "my-dirname"
    }, '1')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='1')

    day = datetime.now().strftime('%A')
    await wait_for_data(run_ws_client, 'stdout', 'output', day + '\n', 0, '1')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '1')


@pytest.mark.asyncio
async def test_run_code_relative_path(run_ws_client):
    copy('{}/test_data/print_date.py'.format(E2E_PATH), WORKING_DIRECTORY)

    start_cmd = create_message('start', {
        'runner': 'python3', 'path': 'print_date.py'
    }, '1')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='1')

    day = datetime.now().strftime('%A')
    await wait_for_data(run_ws_client, 'stdout', 'output', day + '\n', 0, '1')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '1')


@pytest.mark.asyncio
async def test_run_code_absolute_path(run_ws_client):
    start_cmd = create_message('start', {
        'runner': 'python3',
        'path': "{}/test_data/print_date.py".format(E2E_PATH)
    }, '1')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='1')

    day = datetime.now().strftime('%A')
    await wait_for_data(run_ws_client, 'stdout', 'output', day + '\n', 0, '1')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '1')


@pytest.mark.asyncio
@pytest.mark.parametrize('query_params', [{'user': 'pi'}])
@pytest.mark.skip(reason="Won't work unless run as root on rpi")
async def test_run_as_user(run_ws_client_query):
    code = 'import getpass\nprint(getpass.getuser())'
    start_cmd = create_message('start', {'runner': 'python3', 'code': code},
                               '1')
    await run_ws_client_query.send_str(start_cmd)

    await receive_data(run_ws_client_query, 'started', process='1')

    await wait_for_data(run_ws_client_query, 'stdout', 'output', 'pi\n', 0,
                        '1')

    await wait_for_data(run_ws_client_query, 'stopped', 'exitCode', 0, 0, '1')


@pytest.mark.asyncio
@pytest.mark.parametrize('query_params', [{'pty': '1'}])
async def test_input_pty(run_ws_client_query):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message('start', {'runner': 'python3', 'code': code},
                               '1')
    await run_ws_client_query.send_str(start_cmd)

    await receive_data(run_ws_client_query, 'started', process='1')

    user_input = create_message('stdin', {'input': 'hello\r'}, '1')
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(run_ws_client_query, 'stdout', 'output',
                        'hello\r\nHUH?! SPEAK UP, SONNY!\r\n', 0, '1')

    user_input = create_message('stdin', {'input': 'HEY GRANDMA\r'}, '1')
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(run_ws_client_query, 'stdout', 'output',
                        'HEY GRANDMA\r\nNO, NOT SINCE 1930\r\n', 0, '1')

    user_input = create_message('stdin', {'input': 'BYE\r'}, '1')
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(run_ws_client_query, 'stdout', 'output', 'BYE\r\n', 0,
                        '1')

    await wait_for_data(run_ws_client_query, 'stopped', 'exitCode', 0, 0, '1')
