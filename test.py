import pytest

from src import app

def test_status():
    client = app.test_client()
    r = client.get('/status')
    assert '200 OK' == r.status
    assert 'OK' == r.data.decode("utf-8")
