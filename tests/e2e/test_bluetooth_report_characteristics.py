import asyncio

from further_link.util.bluetooth.gatt import (
    PT_APT_VERSION_READ_CHARACTERISTIC_UUID,
    PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.utils import bytearray_to_dict


def test_status_characteristic_read(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_STATUS_CHARACTERISTIC_UUID
    )
    assert bluetooth_client.server.read(char) == b"OK"


def test_version_characteristic_read(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_VERSION_CHARACTERISTIC_UUID
    )
    assert bluetooth_client.server.read(char) == b'{"version": "0.0.1.dev1"}'


async def test_apt_version(bluetooth_client):
    assert bluetooth_client is not None
    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID
    )
    bluetooth_client.server.write(char, b"python3")

    await asyncio.sleep(0.5)

    resp = bytearray_to_dict(
        bluetooth_client.read_value(PT_APT_VERSION_READ_CHARACTERISTIC_UUID)
    )

    assert "version" in resp
    assert resp["version"].startswith("3")
