import pytest
import requests

def test_status():
    r = requests.get('http://localhost:8080/status')
    assert 'OK' in r.text

test_status()
