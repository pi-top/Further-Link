# Mock https://github.com/spacecheese/bluez_peripheral/blob/master/bluez_peripheral/gatt/service.py
import inspect
from typing import List

from bluez_peripheral.uuid16 import UUID16

from tests.mocks.bluetooth.characteristic import characteristicMock


class ServiceMock:
    _INTERFACE = "org.bluez.GattService1"

    def _populate(self):
        # Only interested in characteristic members.
        members = inspect.getmembers(
            type(self), lambda m: type(m) is characteristicMock
        )

        for _, member in members:
            member._set_service(self)

            # Some characteristics will occur multiple times due to different decorators.
            if member not in self._characteristics:
                self.add_characteristic(member)

    def __init__(
        self,
        uuid,
        primary: bool = True,
        includes=[],
    ):
        self._uuid = UUID16.parse_uuid(uuid)
        self._primary = primary
        self._characteristics: List = []
        self._path = None
        self._includes = includes
        self._populate()

    def is_registered(self) -> bool:
        return self._path is not None

    def add_characteristic(self, char):
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.append(char)

    def remove_characteristic(self, char):
        if self.is_registered():
            raise ValueError(
                "Registered services cannot be modified. Please unregister the containing application."
            )

        self._characteristics.remove(char)

    def _export(self, bus, path: str):
        pass

    def _unexport(self, bus):
        pass

    async def register(
        self,
        bus,
        path: str = "/com/spacecheese/bluez_peripheral",
        adapter=None,
    ):
        pass

    async def unregister(self):
        pass

    @property
    def UUID(self):
        return str(self._uuid)

    @property
    def Primary(self):
        return self._primary

    @property
    def Includes(self):
        paths = []

        for service in self._includes:
            if service._path is not None:
                paths.append(service._path)

        paths.append(self._path)
        return paths
