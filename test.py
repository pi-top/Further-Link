import pytest
import asyncio
import websockets
import subprocess
import ssl
from datetime import datetime
from time import sleep

from server import run
from src.message import create_message, parse_message


@pytest.fixture(scope='session', autouse=True)
def db_conn():
    command = ['python3', 'server.py']
    proc = subprocess.Popen(command)
    sleep(1)
    yield
    proc.terminate()


uri = 'ws://localhost:8028/'
sslopts = {"cert_reqs": ssl.CERT_NONE}


# def test_status():
#     r = http_client.get('/status')
#     assert '200 OK' == r.status
#     assert 'OK' == r.data.decode('utf-8')


@pytest.mark.asyncio
async def test_bad_message():
    print('test')
    async with websockets.connect(uri) as client:
        start_cmd = create_message('start')
        print('1')
        await client.send(start_cmd)
        print('2')

        m_type, m_data = parse_message(await client.recv())
        print('3')
        assert m_type == 'error'
        assert m_data == {'message': 'Bad message'}
        print('4')


@pytest.mark.asyncio
async def test_run_code():
    async with websockets.connect(uri) as client:

        code = 'from datetime import datetime\nprint(datetime.now().strftime("%A"))'
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        m_type, m_data = parse_message(await client.recv())
        day = datetime.now().strftime('%A')
        assert m_type == 'stdout'
        assert m_data == {'output': day + '\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_stop_early():
    async with websockets.connect(uri) as client:
        code = "while True: pass"
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        stop_cmd = create_message('stop')
        await client.send(stop_cmd)

        m_type, m_data = parse_message(await client.recv())
        print(m_data)
        assert m_type == 'stopped'
        assert m_data == {'exitCode': -15}


@pytest.mark.asyncio
async def test_bad_code():
    async with websockets.connect(uri) as client:
        code = "i'm not valid python"
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stderr'
        assert m_data['output'].startswith('  File')

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stderr'
        assert m_data == {'output': '    i\'m not valid python\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stderr'
        assert m_data == {'output': '                       ^\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stderr'
        assert m_data == {'output': 'SyntaxError: EOL while scanning string literal\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': 1}


@pytest.mark.asyncio
async def test_input():
    async with websockets.connect(uri) as client:
        code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        user_input = create_message('stdin', {'input': 'hello\n'})
        await client.send(user_input)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stdout'
        assert m_data == {'output': 'HUH?! SPEAK UP, SONNY!\n'}

        user_input = create_message('stdin', {'input': 'HEY GRANDMA\n'})
        await client.send(user_input)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stdout'
        assert m_data == {'output': 'NO, NOT SINCE 1930\n'}

        user_input = create_message('stdin', {'input': 'BYE\n'})
        await client.send(user_input)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': 0}


@pytest.mark.asyncio
async def test_two_clients():
    async with websockets.connect(uri) as client:
        async with websockets.connect(uri) as client2:
            code = "while True: pass"
            start_cmd = create_message('start', {'sourceScript': code})
            await client.send(start_cmd)

            m_type, m_data = parse_message(await client.recv())
            assert m_type == 'started'

            await client2.send(start_cmd)

            m_type, m_data = parse_message(await client2.recv())
            assert m_type == 'started'

            stop_cmd = create_message('stop')
            await client.send(stop_cmd)

            m_type, m_data = parse_message(await client.recv())
            assert m_type == 'stopped'
            assert m_data == {'exitCode': -15}

            stop_cmd = create_message('stop')
            await client2.send(stop_cmd)

            m_type, m_data = parse_message(await client2.recv())
            assert m_type == 'stopped'
            assert m_data == {'exitCode': -15}


@pytest.mark.asyncio
async def test_out_of_order_commands():
    async with websockets.connect(uri) as client:
        # send input
        user_input = create_message('stdin', {'input': 'hello\n'})
        await client.send(user_input)

        # bad message
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'error'
        assert m_data == {'message': 'Bad message'}

        # send stop
        stop_cmd = create_message('stop')
        await client.send(stop_cmd)

        # bad message
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'error'
        assert m_data == {'message': 'Bad message'}

        # send start
        code = "while True: pass"
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        # started
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        # send start
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        # bad message
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'error'
        assert m_data == {'message': 'Bad message'}

        # send stop
        stop_cmd = create_message('stop')
        await client.send(stop_cmd)

        # stopped
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': -15}

        # send stop
        stop_cmd = create_message('stop')
        await client.send(stop_cmd)

        # bad message
        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'error'
        assert m_data == {'message': 'Bad message'}


@pytest.mark.asyncio
async def test_discard_old_input():
    async with websockets.connect(uri) as client:
        code = 'print("hello world")'
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        unterminated_input = create_message('stdin', {'input': 'unterminated input'})
        await client.send(unterminated_input)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stdout'
        assert m_data == {'output': 'hello world\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': 0}

        code = 'print(input())'
        start_cmd = create_message('start', {'sourceScript': code})
        await client.send(start_cmd)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'started'

        user_input = create_message('stdin', {'input': 'hello\n'})
        await client.send(user_input)

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stdout'
        assert m_data == {'output': 'hello\n'}

        m_type, m_data = parse_message(await client.recv())
        assert m_type == 'stopped'
        assert m_data == {'exitCode': 0}
