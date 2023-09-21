import logging
from asyncio import AbstractEventLoop
from typing import Callable, Dict, Optional
from uuid import UUID

from bless.backends.characteristic import (
    GATTAttributePermissions,
    GATTCharacteristicProperties,
)
from bless.backends.server import BaseBlessServer

from .characteristic import BlessGATTCharacteristicMock
from .service import BlessGATTServiceMock


class BlessServerMock(BaseBlessServer):
    def __init__(self, name: str, loop: Optional[AbstractEventLoop] = None, **kwargs):
        super(BlessServerMock, self).__init__(loop=loop, **kwargs)
        self.name: str = name
        self._adapter: Optional[str] = kwargs.get("adapter", None)

        self._char_observer: Dict = {}

    async def setup(self):
        pass

    async def start(self, **kwargs) -> bool:
        return True

    async def stop(self) -> bool:
        return True

    async def is_connected(self) -> bool:
        return True

    async def is_advertising(self) -> bool:
        return True

    async def add_new_service(self, uuid: str):
        if uuid not in self.services:
            logging.debug(f"Adding new service with {uuid}")
            self.services[uuid] = BlessGATTServiceMock(uuid)

    async def add_new_characteristic(
        self,
        service_uuid: str,
        char_uuid: str,
        properties: GATTCharacteristicProperties,
        value: Optional[bytearray],
        permissions: GATTAttributePermissions,
    ):
        service = self.services[service_uuid]
        characteristic = BlessGATTCharacteristicMock(
            char_uuid, properties, permissions, value
        )
        await characteristic.init(service)

        logging.debug(
            f"Adding new characteristic with uuid {char_uuid} to service {service_uuid}"
        )

        self.services[service_uuid].add_characteristic(characteristic)

    def update_value(self, service_uuid: str, char_uuid: str) -> bool:
        service_uuid = str(UUID(service_uuid))
        char_uuid = str(UUID(char_uuid))

        service = self.get_service(service_uuid)
        if service is None:
            return False

        characteristic = service.get_characteristic(char_uuid)
        value = characteristic.value

        # this handles subscribers, which is done using dbus in bless
        for callback in self._char_observer.get(char_uuid, []):
            callback(value)

        return True

    def _subscribe_to_characteristic(self, char_uuid: str, callback: Callable):
        if char_uuid not in self._char_observer:
            self._char_observer[char_uuid] = []
        self._char_observer[char_uuid].append(callback)

    def read(self, char: BlessGATTCharacteristicMock) -> bytes:
        return bytes(self.read_request(char.uuid))

    def write(self, char: BlessGATTCharacteristicMock, value: bytes):
        return self.write_request(char.uuid, bytearray(value))
