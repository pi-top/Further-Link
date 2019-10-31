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
