import asyncio
import logging
from os import environ
from typing import List, Optional

from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.util import Adapter, get_message_bus

from further_link.util.bluetooth.service import FurtherGattService
from further_link.util.bluetooth.utils import get_bluetooth_server_name


class BluetoothServer:
    _services_cls = [FurtherGattService]
    services: List

    def __init__(self) -> None:
        self.services = [service() for service in self._services_cls]
        self.bus = None

    def get_service(self, uuid: str) -> Optional[Service]:
        for service in self.services:
            if service.UUID == uuid:
                return service
        return None

    async def start(self):
        logging.debug("Starting bluetooth server...")
        self.bus = await get_message_bus()
        adapter = await Adapter.get_first(self.bus)

        # DEBUG: avoids use of miniscreen for pairing
        if environ.get("FURTHER_LINK_NO_MINISCREEN_PAIRING") == "true":
            advert = Advertisement(
                localName=get_bluetooth_server_name(),
                serviceUUIDs=[service.UUID for service in self.services],
                appearance=0,
                timeout=0,
            )
            await advert.register(self.bus, adapter)

            agent = NoIoAgent()
            await agent.register(self.bus)

        for service in self.services:
            await service.register(self.bus, adapter=adapter)

        logging.info("Started bluetooth server")

    def stop(self):
        logging.info("Stopping bluetooth server...")
        if self.bus:
            self.bus.disconnect()


if __name__ == "__main__":
    server = BluetoothServer()
    asyncio.run(server.start())
