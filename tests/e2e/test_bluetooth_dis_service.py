import struct

import pytest

from further_link.util.bluetooth.uuids import (
    DIS_MANUFACTURER_NAME_UUID,
    DIS_MODEL_NUMBER_UUID,
    DIS_PNP_ID_UUID,
    DIS_SERVICE_UUID,
)
from further_link.version import __version__


@pytest.fixture
def dis_service(bluetooth_server):
    assert bluetooth_server is not None
    service = bluetooth_server.get_service(DIS_SERVICE_UUID)
    assert service is not None
    yield service


def test_dis_manufacturer_name(dis_service):
    char = dis_service.get_characteristic(DIS_MANUFACTURER_NAME_UUID)
    value = char.getter_func(dis_service, {})

    # Verify the returned bytearray contains the expected manufacturer name
    assert value == bytearray("pi-top", "utf-8")


def test_dis_model_number(dis_service):
    char = dis_service.get_characteristic(DIS_MODEL_NUMBER_UUID)
    value = char.getter_func(dis_service, {})

    # Verify the returned bytearray contains the expected model number
    assert value == bytearray("pi-top [4]", "utf-8")


def test_dis_pnp_id(dis_service):
    char = dis_service.get_characteristic(DIS_PNP_ID_UUID)
    value = char.getter_func(dis_service, {})

    # PNP ID is a structured binary value with specific format
    # First byte should be 1 (Vendor ID Source = Bluetooth SIG)
    assert len(value) == 7  # Should be 7 bytes total
    assert value[0] == 1  # Vendor ID Source = 1 (Bluetooth SIG)

    # Extract values from the struct format used in dis_service.py
    vendor_id_source, vendor_id, product_id, product_version = struct.unpack(
        "<BHHH", value
    )

    # Verify values match those in the implementation
    assert vendor_id_source == 1
    assert vendor_id == 0x0590  # Vendor ID from the implementation
    assert product_id == 0x0001  # Product ID for pi-top [4]

    # Check product version is derived from __version__
    version_parts = __version__.split(".")
    expected_major = int(version_parts[0]) if len(version_parts) > 0 else 0
    expected_minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    expected_product_version = (expected_major << 8) | expected_minor

    assert product_version == expected_product_version


def test_dis_service_existence(dis_service):
    # Verify service exists and is properly configured
    assert dis_service.Primary is True

    # Verify all three characteristics exist
    manufacturer_char = dis_service.get_characteristic(DIS_MANUFACTURER_NAME_UUID)
    model_char = dis_service.get_characteristic(DIS_MODEL_NUMBER_UUID)
    pnp_char = dis_service.get_characteristic(DIS_PNP_ID_UUID)

    assert manufacturer_char is not None
    assert model_char is not None
    assert pnp_char is not None
