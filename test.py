import pytest
import threading
import asyncio
import websocket
import json
from datetime import datetime

from run import run, app

http_client = app.test_client()

server = threading.Thread(target=run, daemon=True)
server.start()
websocket_client = websocket.WebSocket()
websocket_client.connect("ws://localhost:8080/exec")

def test_status():
    r = http_client.get('/status')
    assert '200 OK' == r.status
    assert 'OK' == r.data.decode("utf-8")

def test_bad_message():
    websocket_client.connect("ws://localhost:8080/exec")
    start_cmd = json.dumps({"type":"start"})
    websocket_client.send(start_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"error", "data": {"message": "Bad message"}}

def test_run_code():
    websocket_client.connect("ws://localhost:8080/exec")
    code = "from datetime import datetime\nprint(datetime.now().strftime('%A'))"
    start_cmd = json.dumps({
        "type": "start",
        "data": { "sourceScript": code }
    })
    websocket_client.send(start_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"started"}

    r = json.loads(websocket_client.recv())
    day = datetime.now().strftime('%A')
    assert r == { "type" : "stdout", "data" : {"output": day + '\n' }}

    r = json.loads(websocket_client.recv())
    assert r == {"type":"stopped", "data": { "exitCode": 0 }}

def test_stop_early():
    websocket_client.connect("ws://localhost:8080/exec")
    code = "while True: pass"
    start_cmd = json.dumps({
        "type": "start",
        "data": { "sourceScript": code }
    })
    websocket_client.send(start_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"started"}

    stop_cmd = json.dumps({ "type": "stop" })
    websocket_client.send(stop_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"stopped", "data": { "exitCode": -9 }}

def test_bad_code():
    websocket_client.connect("ws://localhost:8080/exec")
    code = "i'm not valid python"
    start_cmd = json.dumps({
        "type": "start",
        "data": { "sourceScript": code }
    })
    websocket_client.send(start_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"started"}

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stderr",
        "data": {
            "output": "  File \"<string>\", line 1\n"
        }
    }

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stderr",
        "data": {
            "output": "    i'm not valid python\n"
        }
    }

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stderr",
        "data": {
            "output": "                       ^\n"
        }
    }

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stderr",
        "data": {
            "output": "SyntaxError: EOL while scanning string literal\n"
        }
    }

    r = json.loads(websocket_client.recv())
    assert r == {"type":"stopped", "data": { "exitCode": 1 }}

def test_input():
    websocket_client.connect("ws://localhost:8080/exec")
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = json.dumps({
        "type": "start",
        "data": { "sourceScript": code }
    })
    websocket_client.send(start_cmd)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"started"}

    user_input = json.dumps({
        "type": "stdin",
        "data": { "input": "hello" }
    })
    websocket_client.send(user_input)

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stdout",
        "data": {
            "output": "HUH?! SPEAK UP, SONNY!"
        }
    }

    user_input = json.dumps({
        "type": "stdin",
        "data": { "input": "HEY GRANDMA" }
    })
    websocket_client.send(user_input)

    r = json.loads(websocket_client.recv())
    assert r == {
        "type":"stdout",
        "data": {
            "output": "NO, NOT SINCE 1930"
        }
    }

    user_input = json.dumps({
        "type": "stdin",
        "data": { "input": "BYE" }
    })
    websocket_client.send(user_input)

    r = json.loads(websocket_client.recv())
    assert r == {"type":"stopped", "data": { "exitCode": 0 }}