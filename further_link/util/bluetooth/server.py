import asyncio
import logging
from os import environ

from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from bluez_peripheral.util import Adapter, get_message_bus

from further_link.util.bluetooth.dis_service import DeviceInformationService
from further_link.util.bluetooth.service import FurtherGattService
from further_link.util.bluetooth.utils import get_bluetooth_server_name


class BluetoothServer:
    _services_cls = [FurtherGattService, DeviceInformationService]

    def __init__(self) -> None:
        self._adapter = None
        self._next_service_id = 0
        self.services = []
        self.bus = None

        # Initialize services with unique paths
        for service_cls in self._services_cls:
            service_path = (
                f"/com/spacecheese/bluez_peripheral/service{self._next_service_id}"
            )
            self._next_service_id += 1

            service_instance = service_cls()
            if hasattr(service_instance, "set_path"):
                service_instance.set_path(service_path)
            service_instance._path = (
                service_path  # Set path directly if no set_path method
            )
            self.services.append(service_instance)

    async def start(self):
        logging.debug("Starting bluetooth server...")
        self.bus = await get_message_bus()
        self._adapter = await Adapter.get_first(self.bus)

        # Configure advertisement
        if environ.get("FURTHER_LINK_BLUETOOTH_PAIR_AND_ADVERTISE") in ("1", "true"):
            advert = Advertisement(
                localName=get_bluetooth_server_name(),
                serviceUUIDs=[service.UUID for service in self.services],
                appearance=0x0340,  # Generic Computer appearance value
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
