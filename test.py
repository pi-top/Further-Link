import pytest
import threading
import asyncio
import websocket

from run import run, app

server = threading.Thread(target=run, daemon=True)
server.start()

http_client = app.test_client()

websocket_client = websocket.WebSocket()
websocket_client.connect("ws://localhost:8080/exec")

def test_status():
    r = http_client.get('/status')
    assert '200 OK' == r.status
    assert 'OK' == r.data.decode("utf-8")

def test_echo():
    websocket_client.send('echo...echo')
    r = websocket_client.recv()
    assert r == 'echo...echo'
