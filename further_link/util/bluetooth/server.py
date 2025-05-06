import asyncio
import logging
from os import environ
from typing import Optional

from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.util import Adapter, get_message_bus

from further_link.util.bluetooth.dis_service import DeviceInformationService
from further_link.util.bluetooth.service import FurtherGattService
from further_link.util.bluetooth.utils import (
    find_object_with_uuid,
    get_bluetooth_server_name,
)
from further_link.util.bluetooth.values import APPEARANCE


class BluetoothServer:
    _services_cls = [DeviceInformationService, FurtherGattService]

    def __init__(self) -> None:
        self._adapter = None
        self._next_service_id = 0
        self.services = []
        self.bus = None

        # Initialize services with unique paths
        for service_cls in self._services_cls:
            if service_cls == DeviceInformationService:
                # Use a path that should take precedence to avoid conflicts with BlueZ's DIS
                service_path = "/org/bluez/hci0/service_dis"
            else:
                service_path = (
                    f"/com/spacecheese/bluez_peripheral/service{self._next_service_id}"
                )
                self._next_service_id += 1

            service_instance = service_cls()
            if hasattr(service_instance, "set_path"):
                service_instance.set_path(service_path)
            service_instance._path = service_path
            self.services.append(service_instance)

    def get_service(self, uuid: str) -> Optional[Service]:
        return find_object_with_uuid(self.services, uuid)

    async def start(self):
        logging.debug("Starting bluetooth server...")
        self.bus = await get_message_bus()
        self._adapter = await Adapter.get_first(self.bus)

        # For development purposes; keep pairing mode on if env var is set
        if environ.get("FURTHER_LINK_BLUETOOTH_PAIR_AND_ADVERTISE", "0").lower() in (
            "1",
            "true",
        ):
            advert = Advertisement(
                localName=get_bluetooth_server_name(),
                serviceUUIDs=[service.UUID for service in self.services],
                appearance=APPEARANCE,
                timeout=0,
            )
            await advert.register(self.bus, self._adapter)

            agent = NoIoAgent()
            await agent.register(self.bus)

        for service in self.services:
            await service.register(self.bus, adapter=self._adapter, path=service._path)
        logging.info("Started bluetooth server")

    def stop(self):
        logging.info("Stopping bluetooth server...")
        for service in self.services:
            try:
                service.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up service: {e}")
        if self.bus:
            self.bus.disconnect()


if __name__ == "__main__":
    server = BluetoothServer()
    asyncio.run(server.start())
