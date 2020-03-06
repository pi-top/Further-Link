import os
import subprocess
from time import sleep
from datetime import datetime

import pytest
import aiohttp

from src.message import create_message, parse_message

BASE_URI = 'ws://0.0.0.0:8028'
WS_URI = BASE_URI + '/run-py'
STATUS_URI = BASE_URI + '/status'

ENV = os.environ.copy()
ENV["FURTHER_LINK_NOSSL"] = "true"
@pytest.fixture(scope='session', autouse=True)
def start_server():
    command = ['python3', 'server.py']
    proc = subprocess.Popen(command,
                            env=ENV,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT)
    sleep(1)
    yield
    proc.terminate()


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
    print('1')
    await ws_client.send_str(start_cmd)
    print('2')

    m_type, m_data = parse_message((await ws_client.receive()).data)
    print('3')
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}
    print('4')


@pytest.mark.asyncio
async def test_run_code(ws_client):
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
async def test_stop_early(ws_client):
    code = "while True: pass"
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    stop_cmd = create_message('stop')
    await ws_client.send_str(stop_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    print(m_data)
    assert m_type == 'stopped'
    assert m_data == {'exitCode': -15}


@pytest.mark.asyncio
async def test_bad_code(ws_client):
    code = "i'm not valid python"
    start_cmd = create_message('start', {'sourceScript': code})
    await ws_client.send_str(start_cmd)

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'started'

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    assert m_data['output'].startswith('  File')

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    assert m_data == {'output': '    i\'m not valid python\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    assert m_data == {'output': '                       ^\n'}

    m_type, m_data = parse_message((await ws_client.receive()).data)
    assert m_type == 'stderr'
    assert m_data == {'output': 'SyntaxError: EOL while scanning string literal\n'}

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
            code = "while True: pass"
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
    code = "while True: pass"
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

    unterminated_input = create_message('stdin', {'input': 'unterminated input'})
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
