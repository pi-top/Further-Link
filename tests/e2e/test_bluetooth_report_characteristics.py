import asyncio

from further_link.util.bluetooth.gatt import (
    PT_APT_VERSION_READ_CHARACTERISTIC_UUID,
    PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.utils import bytearray_to_dict

from .helpers import send_formatted_bluetooth_message


def test_status_characteristic_read(bluetooth_server):
    assert bluetooth_server is not None
    char = bluetooth_server.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_STATUS_CHARACTERISTIC_UUID
    )
    value = bluetooth_server.server.read(char)

    chunk = Chunk(value)
    assert chunk.message == value
    assert chunk.payload == b"OK"
    assert chunk.current_index == 0
    assert chunk.total_chunks == 1
    assert isinstance(chunk.id, int)
    assert chunk.id < 65536


def test_version_characteristic_read(bluetooth_server):
    assert bluetooth_server is not None
    char = bluetooth_server.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_VERSION_CHARACTERISTIC_UUID
    )
    value = bluetooth_server.server.read(char)

    chunk = Chunk(value)
    assert chunk.message == value
    assert chunk.payload == b'{"version": "0.0.1.dev1"}'
    assert chunk.current_index == 0
    assert chunk.total_chunks == 1
    assert isinstance(chunk.id, int)
    assert chunk.id < 65536


async def test_apt_version(bluetooth_server):
    char = bluetooth_server.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID
    )
    await send_formatted_bluetooth_message(bluetooth_server, char, "python3")
    await asyncio.sleep(0.3)

    char = bluetooth_server.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_APT_VERSION_READ_CHARACTERISTIC_UUID
    )
    value = bluetooth_server.server.read(char)

    chunk = Chunk(value)
    assert chunk.message == value
    assert chunk.current_index == 0
    assert chunk.total_chunks == 1
    assert isinstance(chunk.id, int)
    assert chunk.id < 65536

    resp = bytearray_to_dict(chunk.payload)
    assert "version" in resp
    assert resp["version"].startswith("3")
