import pytest
import threading
import asyncio
import websocket
import time
import json

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

def test_start():
    websocket_client.connect("ws://localhost:8080/exec")
    start_cmd = json.dumps({"type":"start"})
    websocket_client.send(start_cmd)
    r = websocket_client.recv()
    assert r == '{"type":"started"}'

def test_runstuff():
    websocket_client.connect("ws://localhost:8080/exec")
    start_cmd = json.dumps({"type":"start", "data": {"sourceScript":"print('hi')"}})
    websocket_client.send(start_cmd)
    r = websocket_client.recv()
    assert r == '{"type":"started"}'
    r = json.loads(websocket_client.recv())
    assert r == { "type" : "stdout", "data" : {"output":"hi"}}