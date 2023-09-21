import logging
from typing import Callable, Dict

from bless import GATTAttributePermissions, GATTCharacteristicProperties

PT_RUN_SERVICE_UUID = "12341000-1234-1234-1234-123456789abc"
PT_RUN_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789abd"
PT_STATUS_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789abe"
PT_VERSION_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789abf"
PT_UPLOAD_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789acf"

FURTHER_GATT_CONFIG = {
    PT_RUN_SERVICE_UUID: {
        PT_RUN_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.write
                | GATTCharacteristicProperties.read
                | GATTCharacteristicProperties.notify
            ),
            "Permissions": (
                GATTAttributePermissions.readable | GATTAttributePermissions.writeable
            ),
            "Value": None,
        },
        PT_STATUS_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
            ),
            "Permissions": (GATTAttributePermissions.readable),
            "Value": None,
        },
        PT_VERSION_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
            ),
            "Permissions": (GATTAttributePermissions.readable),
            "Value": None,
        },
        PT_UPLOAD_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.write
                | GATTCharacteristicProperties.read
                | GATTCharacteristicProperties.notify
            ),
            "Permissions": (
                GATTAttributePermissions.readable | GATTAttributePermissions.writeable
            ),
            "Value": None,
        },
    },
}


class GattConfig:
    def __init__(self, name: str, tree: Dict) -> None:
        self.name = name
        self.tree = tree

    def register_read_handler(
        self, service_uuid: str, characteristic_uuid: str, handler: Callable
    ) -> None:
        try:
            self.tree[service_uuid][characteristic_uuid]["ReadHandler"] = handler
        except Exception as e:
            logging.error(f"Unable to register handler: {e}")

    def register_write_handler(
        self, service_uuid: str, characteristic_uuid: str, handler: Callable
    ) -> None:
        try:
            self.tree[service_uuid][characteristic_uuid]["WriteHandler"] = handler
        except Exception as e:
            logging.error(f"Unable to register handler: {e}")
