import pytest
import asyncio
import websocket
import ssl
from datetime import datetime

from src import run
from src.message import create_message, parse_message

loop = asyncio.new_event_loop()
run(loop)


def new_websocket_client():
    client = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
    client.connect('ws://localhost:8028/')
    return client


# def test_status():
#     r = http_client.get('/status')
#     assert '200 OK' == r.status
#     assert 'OK' == r.data.decode('utf-8')


def test_bad_message():
    websocket_client = new_websocket_client()

    start_cmd = create_message('start')
    websocket_client.send(start_cmd)

    m_type, m_data = parse_message(websocket_client.recv())
    assert m_type == 'error'
    assert m_data == {'message': 'Bad message'}


# def test_run_code():
#     websocket_client = new_websocket_client()
#
#     code = 'from datetime import datetime\nprint(datetime.now().strftime("%A"))'
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     day = datetime.now().strftime('%A')
#     assert m_type == 'stdout'
#     assert m_data == {'output': day + '\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 0}
#
#
# def test_stop_early():
#     websocket_client = new_websocket_client()
#
#     code = "while True: pass"
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     stop_cmd = create_message('stop')
#     websocket_client.send(stop_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     print(m_data)
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': -9}
#
#
# def test_bad_code():
#     websocket_client = new_websocket_client()
#
#     code = "i'm not valid python"
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stderr'
#     assert m_data['output'].startswith('  File')
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stderr'
#     assert m_data == {'output': '    i\'m not valid python\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stderr'
#     assert m_data == {'output': '                       ^\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stderr'
#     assert m_data == {'output': 'SyntaxError: EOL while scanning string literal\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 1}
#
#
# def test_input():
#     websocket_client = new_websocket_client()
#
#     code = """s = input()
# while "BYE" != s:
#     print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
#     s = input()"""
#
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     user_input = create_message('stdin', {'input': 'hello\n'})
#     websocket_client.send(user_input)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stdout'
#     assert m_data == {'output': 'HUH?! SPEAK UP, SONNY!\n'}
#
#     user_input = create_message('stdin', {'input': 'HEY GRANDMA\n'})
#     websocket_client.send(user_input)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stdout'
#     assert m_data == {'output': 'NO, NOT SINCE 1930\n'}
#
#     user_input = create_message('stdin', {'input': 'BYE\n'})
#     websocket_client.send(user_input)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 0}
#
#
# def test_two_clients():
#     websocket_client = new_websocket_client()
#     websocket_client2 = new_websocket_client()
#
#     code = "while True: pass"
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     websocket_client2.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client2.recv())
#     assert m_type == 'started'
#
#     stop_cmd = create_message('stop')
#     websocket_client.send(stop_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': -9}
#
#     stop_cmd = create_message('stop')
#     websocket_client2.send(stop_cmd)
#
#     m_type, m_data = parse_message(websocket_client2.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': -9}
#
#
# def test_out_of_order_commands():
#     websocket_client = new_websocket_client()
#
#     # send input
#     user_input = create_message('stdin', {'input': 'hello\n'})
#     websocket_client.send(user_input)
#
#     # bad message
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'error'
#     assert m_data == {'message': 'Bad message'}
#
#     # send stop
#     stop_cmd = create_message('stop')
#     websocket_client.send(stop_cmd)
#
#     # bad message
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'error'
#     assert m_data == {'message': 'Bad message'}
#
#     # send start
#     code = "while True: pass"
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     # started
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     # send start
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     # bad message
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'error'
#     assert m_data == {'message': 'Bad message'}
#
#     # send stop
#     stop_cmd = create_message('stop')
#     websocket_client.send(stop_cmd)
#
#     # stopped
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': -9}
#
#     # send stop
#     stop_cmd = create_message('stop')
#     websocket_client.send(stop_cmd)
#
#     # bad message
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'error'
#     assert m_data == {'message': 'Bad message'}
#
#
# def test_discard_old_input():
#     websocket_client = new_websocket_client()
#
#     code = 'print("hello world")'
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     unterminated_input = create_message('stdin', {'input': 'unterminated input'})
#     websocket_client.send(unterminated_input)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stdout'
#     assert m_data == {'output': 'hello world\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 0}
#
#     code = 'print(input())'
#     start_cmd = create_message('start', {'sourceScript': code})
#     websocket_client.send(start_cmd)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'started'
#
#     user_input = create_message('stdin', {'input': 'hello\n'})
#     websocket_client.send(user_input)
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stdout'
#     assert m_data == {'output': 'hello\n'}
#
#     m_type, m_data = parse_message(websocket_client.recv())
#     assert m_type == 'stopped'
#     assert m_data == {'exitCode': 0}
