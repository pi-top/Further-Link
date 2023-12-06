import logging
from typing import Callable, Dict

from bless import GATTAttributePermissions, GATTCharacteristicProperties

PT_SERVICE_UUID = "12341000-1234-1234-1234-123456789aaa"
PT_STATUS_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789aba"
PT_VERSION_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789aca"
PT_APT_VERSION_READ_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789ada"
PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789adb"


# TODO: upload & run characteristics should run in a separate service (not supported by bless apparently)
PT_UPLOAD_READ_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789bba"
PT_UPLOAD_WRITE_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789bca"
PT_RUN_READ_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789cba"
PT_RUN_WRITE_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789cca"


FURTHER_GATT_CONFIG = {
    PT_SERVICE_UUID: {
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
        PT_APT_VERSION_READ_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
            ),
            "Permissions": (GATTAttributePermissions.readable),
            "Value": None,
        },
        PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID: {
            "Properties": (GATTCharacteristicProperties.write),
            "Permissions": (GATTAttributePermissions.writeable),
            "Value": None,
        },
        PT_UPLOAD_READ_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
            ),
            "Permissions": (GATTAttributePermissions.readable),
            "Value": None,
        },
        PT_UPLOAD_WRITE_CHARACTERISTIC_UUID: {
            "Properties": (GATTCharacteristicProperties.write),
            "Permissions": (GATTAttributePermissions.writeable),
            "Value": None,
        },
        PT_RUN_READ_CHARACTERISTIC_UUID: {
            "Properties": (
                GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
            ),
            "Permissions": (GATTAttributePermissions.readable),
            "Value": None,
        },
        PT_RUN_WRITE_CHARACTERISTIC_UUID: {
            "Properties": (GATTCharacteristicProperties.write),
            "Permissions": (GATTAttributePermissions.writeable),
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
