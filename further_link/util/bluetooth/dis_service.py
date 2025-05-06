import logging
import os
import struct
from typing import Optional, Type, Union

from bluez_peripheral.gatt.characteristic import CharacteristicFlags, characteristic
from bluez_peripheral.gatt.service import Service

from further_link.util import state
from further_link.util.bluetooth.utils import find_object_with_uuid
from further_link.util.bluetooth.uuids import (
    DIS_FIRMWARE_REVISION_UUID,
    DIS_HARDWARE_REVISION_UUID,
    DIS_MANUFACTURER_NAME_UUID,
    DIS_MODEL_NUMBER_UUID,
    DIS_PNP_ID_UUID,
    DIS_SERIAL_NUMBER_UUID,
    DIS_SERVICE_UUID,
    DIS_SOFTWARE_REVISION_UUID,
    DIS_SYSTEM_ID_UUID,
)
from further_link.util.bluetooth.values import (
    FIRMWARE_REVISION,
    HARDWARE_REVISION,
    MANUFACTURER,
    MODEL_NUMBER,
    PRODUCT_ID,
    SERIAL_NUMBER,
    SYSTEM_ID,
    VENDOR_ID,
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
        logging.debug(f"Read request for manufacturer_name; returning '{MANUFACTURER}'")
        return bytearray(MANUFACTURER, "utf-8")

    @characteristic(DIS_MODEL_NUMBER_UUID, CharFlags.READ)
    def model_number(self, options):
        logging.debug(f"Read request for model_number; returning '{MODEL_NUMBER}'")
        return bytearray(MODEL_NUMBER, "utf-8")

    @characteristic(DIS_PNP_ID_UUID, CharFlags.READ)
    def pnp_id(self, options):
        # PnP ID format according to Bluetooth spec:
        # Vendor ID Source: 1 byte (1 = Bluetooth SIG assigned)
        # Vendor ID: 2 bytes
        # Product ID: 2 bytes
        # Product Version: 2 bytes

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
            VENDOR_ID,
            PRODUCT_ID,
            product_version,
        )

        logging.debug("Read request for pnp_id; returning binary data")
        return bytearray(pnp_data)

    def get_characteristic(self, uuid: str) -> Optional[characteristic]:
        return find_object_with_uuid(self._characteristics, uuid)

    @characteristic(DIS_SERIAL_NUMBER_UUID, CharFlags.READ)
    def serial_number(self, options):
        logging.debug(f"Read request for serial_number; returning '{SERIAL_NUMBER}'")
        return bytearray(SERIAL_NUMBER, "utf-8")

    @characteristic(DIS_FIRMWARE_REVISION_UUID, CharFlags.READ)
    def firmware_revision(self, options):
        logging.debug(
            f"Read request for firmware_revision; returning '{FIRMWARE_REVISION}'"
        )
        return bytearray(FIRMWARE_REVISION, "utf-8")

    @characteristic(DIS_HARDWARE_REVISION_UUID, CharFlags.READ)
    def hardware_revision(self, options):
        logging.debug(
            f"Read request for hardware_revision; returning '{HARDWARE_REVISION}'"
        )
        return bytearray(HARDWARE_REVISION, "utf-8")

    @characteristic(DIS_SOFTWARE_REVISION_UUID, CharFlags.READ)
    def software_revision(self, options):
        logging.debug(f"Read request for software_revision; returning '{__version__}'")
        return bytearray(__version__, "utf-8")

    @characteristic(DIS_SYSTEM_ID_UUID, CharFlags.READ)
    def system_id(self, options):
        logging.debug(f"Read request for system_id; returning '{SYSTEM_ID}'")
        return bytearray(SYSTEM_ID, "utf-8")
