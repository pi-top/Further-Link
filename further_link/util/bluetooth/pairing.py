import asyncio
import logging

import click
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from dbus_next.errors import DBusError

from further_link.util.bluetooth.device import BluetoothDevice
from further_link.util.bluetooth.utils import get_bluetooth_server_name
from further_link.util.bluetooth.uuids import DIS_SERVICE_UUID, PT_SERVICE_UUID
from further_link.util.bluetooth.values import APPEARANCE

PAIRING_TIME = 60


class PairingManager:
    def __init__(self, bluetooth_device: BluetoothDevice):
        self.agent = None
        self.advert = None
        self.bluetooth_device = bluetooth_device

    async def cleanup(self):
        logging.info("Cleaning up Bluetooth resources...")
        try:
            if self.bluetooth_device:
                await self.bluetooth_device.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    async def start_advertisement(self, pairing_time: int, services: list[str]):
        logging.info(
            f"Starting pairing mode and advertisement of {services} for {pairing_time} seconds"
        )
        try:
            self.agent = NoIoAgent()
            assert self.agent is not None
            await self.agent.register(self.bluetooth_device.bus)

            self.advert = Advertisement(
                localName=get_bluetooth_server_name(),
                serviceUUIDs=services,
                appearance=APPEARANCE,
                timeout=pairing_time,
            )
            assert self.advert is not None

            try:
                await self.advert.register(
                    self.bluetooth_device.bus, self.bluetooth_device.adapter
                )
            except DBusError as e:
                if "Failed to register advertisement" in str(e):
                    logging.warning("Attempting to clean up existing advertisements...")
                    raise
                raise

            logging.info("Successfully started pairing mode")
        except Exception as e:
            logging.error(f"Error in pairing mode: {e}")
            raise


async def pairing_mode():
    try:
        bluetooth_device = await BluetoothDevice.create()
        manager = PairingManager(bluetooth_device)
        await manager.start_advertisement(
            timeout=PAIRING_TIME, services=[PT_SERVICE_UUID, DIS_SERVICE_UUID]
        )
        logging.info(
            f"Pairing mode started, sleeping for {manager.pairing_time} seconds"
        )
        await asyncio.sleep(manager.pairing_time)
    except Exception as e:
        logging.error(f"Pairing mode failed: {e}")
    finally:
        logging.info("Pairing time finished, cleaning up")
        await manager.cleanup()


@click.command()
def main():
    asyncio.run(pairing_mode())


if __name__ == "__main__":
    main(prog_name="further-link-bluetooth-pairing")
