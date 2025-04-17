import logging
import os
import struct
from typing import Type, Union

from bluez_peripheral.gatt.characteristic import CharacteristicFlags, characteristic
from bluez_peripheral.gatt.service import Service

from further_link.util import state
from further_link.util.bluetooth.uuids import (
    DIS_MANUFACTURER_NAME_UUID,
    DIS_MODEL_NUMBER_UUID,
    DIS_PNP_ID_UUID,
    DIS_SERVICE_UUID,
)
from further_link.version import __version__


class SecureFlags:
    READ = CharacteristicFlags.ENCRYPT_READ


# Some OS doesn't support protected/secure characteristics
class NonSecureFlags:
    READ = CharacteristicFlags.READ


CharFlags: Union[Type[SecureFlags], Type[NonSecureFlags]] = SecureFlags
if os.environ.get("FURTHER_LINK_NO_BLUETOOTH_ENCRYPTION", "0").lower() in (
    "1",
    "true",
) or state.get("bluetooth", "encrypt", fallback="0").lower() in ("0", "false"):
    logging.info("Using unencrypted bluetooth characteristics for DIS")
    CharFlags = NonSecureFlags


class DeviceInformationService(Service):
    def __init__(self):
        self._path = None
        self._registered = False
        # Set primary=True to indicate this is a primary service
        super().__init__(DIS_SERVICE_UUID, True)

    def set_path(self, path):
        self._path = path

    def cleanup(self):
        if self._registered:
            self.unregister()
            self._registered = False

    @characteristic(DIS_MANUFACTURER_NAME_UUID, CharFlags.READ)
    def manufacturer_name(self, options):
        value = "pi-top"
        logging.debug("Read request for manufacturer_name; returning '%s'", value)
        return bytearray(value, "utf-8")

    @characteristic(DIS_MODEL_NUMBER_UUID, CharFlags.READ)
    def model_number(self, options):
        value = "pi-top [4]"
        logging.debug("Read request for model_number; returning '%s'", value)
        return bytearray(value, "utf-8")

    @characteristic(DIS_PNP_ID_UUID, CharFlags.READ)
    def pnp_id(self, options):
        # PnP ID format according to Bluetooth spec:
        # Vendor ID Source: 1 byte (1 = Bluetooth SIG assigned)
        # Vendor ID: 2 bytes (pi-top: use 0x0590 as placeholder - you should replace with your actual ID)
        # Product ID: 2 bytes (0x0001 for pi-top [4])
        # Product Version: 2 bytes (major.minor: 0x0100 for v1.0)

        # Convert version string to usable product version
        # Get first two version components (major.minor)
        version_parts = __version__.split(".")
        major = int(version_parts[0]) if len(version_parts) > 0 else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        product_version = (major << 8) | minor

        # Pack the data according to the PnP ID characteristic format
        # Format: <vendor_id_source><vendor_id><product_id><product_version>
        # vendor_id_source: 1 byte, vendor_id: 2 bytes (little-endian)
        # product_id: 2 bytes (little-endian), product_version: 2 bytes (little-endian)
        pnp_data = struct.pack(
            "<BHHH",
            1,  # Vendor ID Source (1 = Bluetooth SIG)
            0x0590,  # Vendor ID (replace with actual Bluetooth SIG assigned ID)
            0x0001,  # Product ID for pi-top [4]
            product_version,  # Product Version
        )

        logging.debug("Read request for pnp_id; returning binary data")
        return bytearray(pnp_data)
