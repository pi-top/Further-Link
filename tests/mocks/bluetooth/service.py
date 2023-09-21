from typing import List, Union
from uuid import UUID

from bless.backends.server import BaseBlessServer
from bless.backends.service import BlessGATTService

from .characteristic import BlessGATTCharacteristicMock


class BlessGATTServiceMock(BlessGATTService):
    """ "
    GATT service implementation for the BlueZ backend
    """

    def __init__(self, uuid: Union[str, UUID]):
        super(BlessGATTServiceMock, self).__init__(uuid)
        self.__characteristics: List[BlessGATTCharacteristicMock] = []
        self.__handle = 0

    async def init(self, server: BaseBlessServer):
        return

    @property
    def handle(self) -> int:
        return self.__handle

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def characteristics(self) -> List[BlessGATTCharacteristicMock]:  # type: ignore
        return self.__characteristics

    def add_characteristic(  # type: ignore
        self, characteristic: BlessGATTCharacteristicMock
    ):
        import logging

        logging.info(f"Adding characteristic {characteristic} to service {self}")

        self.__characteristics.append(characteristic)

    @property
    def path(self):
        return self.__path
