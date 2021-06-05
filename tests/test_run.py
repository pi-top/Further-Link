import pytest
from datetime import datetime

from src.message import create_message
from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_bad_message(run_ws_client):
    start_cmd = create_message('start',
                               {'runner': 'python3', 'code': ''})
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, 'error', 'message', 'Bad message')


@pytest.mark.asyncio
async def test_run_code_script(run_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message('start',
                               {'runner': 'python3', 'code': code},
                               '1')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='1')

    day = datetime.now().strftime('%A')
    await wait_for_data(run_ws_client, 'stdout', 'output', day + '\n', 0, '1')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '1')


@pytest.mark.asyncio
async def test_run_two_scripts(run_ws_client):
    code1 = """\
from time import sleep
sleep(1)
print(1)
"""
    code2 = """\
print(2)
"""
    start_cmd = create_message('start',
                               {'runner': 'python3', 'code': code1},
                               '1')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='1')

    start_cmd = create_message('start',
                               {'runner': 'python3', 'code': code2},
                               '2')
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, 'started', process='2')

    await wait_for_data(run_ws_client, 'stdout', 'output', '2\n', 0, '2')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '2')

    await wait_for_data(run_ws_client, 'stdout', 'output', '1\n', 0, '1')

    await wait_for_data(run_ws_client, 'stopped', 'exitCode', 0, 0, '1')
