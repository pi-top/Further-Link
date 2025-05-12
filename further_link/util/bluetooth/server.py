import asyncio
import logging
from os import environ
from typing import Optional

import click
from bluez_peripheral.gatt.service import Service

from further_link.util.bluetooth.device import BluetoothDevice
from further_link.util.bluetooth.dis_service import DeviceInformationService
from further_link.util.bluetooth.pairing import PairingManager
from further_link.util.bluetooth.service import FurtherGattService
from further_link.util.bluetooth.utils import find_object_with_uuid


class BluetoothServer:
    _services_cls = [DeviceInformationService, FurtherGattService]

    def __init__(self, bluetooth_device: BluetoothDevice) -> None:
        self._next_service_id = 0
        self.services = []
        self.bluetooth_device = bluetooth_device

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

        # For development purposes; keep pairing mode on if env var is set
        if environ.get("FURTHER_LINK_BLUETOOTH_PAIR_AND_ADVERTISE", "0").lower() in (
            "1",
            "true",
        ):
            try:
                pairing_manager = PairingManager(self.bluetooth_device)
                await pairing_manager.start_advertisement(
                    timeout=0, services=[service.UUID for service in self.services]
                )
            except Exception as e:
                logging.error(f"Error in pairing mode: {e}")
                await pairing_manager.cleanup()
                raise

        for service in self.services:
            await service.register(
                self.bluetooth_device.bus,
                adapter=self.bluetooth_device.adapter,
                path=service._path,
            )
        logging.info("Started bluetooth server")

    async def stop(self):
        logging.info("Stopping bluetooth server...")
        for service in self.services:
            try:
                service.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up service: {e}")
        if self.bluetooth_device:
            await self.bluetooth_device.cleanup()


async def start_server():
    bluetooth_device = await BluetoothDevice.create()
    server = BluetoothServer(bluetooth_device)
    asyncio.run(server.start())


@click.command()
def main():
    asyncio.run(start_server())


if __name__ == "__main__":
    main(prog_name="further-link-bluetooth-server")
