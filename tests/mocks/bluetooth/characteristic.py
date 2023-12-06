from typing import Optional, Union
from uuid import UUID

from bless.backends.characteristic import (  # noqa: E402
    BlessGATTCharacteristic,
    GATTAttributePermissions,
    GATTCharacteristicProperties,
)
from bless.backends.service import BlessGATTService


class BlessGATTCharacteristicMock(BlessGATTCharacteristic):
    def __init__(
        self,
        uuid: Union[str, UUID],
        properties: GATTCharacteristicProperties,
        permissions: GATTAttributePermissions,
        value: Optional[bytearray],
    ):
        value = value if value is not None else bytearray(b"")
        super().__init__(uuid, properties, permissions, value)
        self.value = value

    async def init(self, service: BlessGATTService):
        return

    @property
    def value(self) -> bytearray:
        """Get the value of the characteristic"""
        return bytearray(self._value)

    @value.setter
    def value(self, val: bytearray):
        """Set the value of the characteristic"""
        self._value = val

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self._uuid

    # XXX: implementation of abstract methods
    def add_descriptor(self):
        return

    def descriptors(self):
        return

    def get_descriptor(self):
        return

    def handle(self):
        return

    def properties(self):
        return

    def service_handle(self):
        return

    def service_uuid(self):
        return
