import asyncio
import logging

import click
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from bluez_peripheral.util import Adapter, get_message_bus
from dbus_next.errors import DBusError

from further_link.util.bluetooth.utils import get_bluetooth_server_name
from further_link.util.bluetooth.uuids import DIS_SERVICE_UUID, PT_SERVICE_UUID
from further_link.util.bluetooth.values import APPEARANCE

PAIRING_TIME = 60


class PairingManager:
    def __init__(self):
        self.bus = None
        self.adapter = None
        self.agent = None
        self.advert = None

    async def cleanup(self):
        logging.info("Cleaning up Bluetooth resources...")
        try:
            if self.bus:
                self.bus.disconnect()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    async def is_bt_card_blocked(self) -> bool:
        """Check if the BT card is blocked by checking if the adapter is powered on."""
        cmd = "rfkill list bluetooth -o Soft -n"
        try:
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            return stdout.decode().strip() == "blocked"
        except Exception as e:
            logging.error(f"Error checking if BT card is blocked: {e}")
            return False

    async def unlock_bt_card(self) -> None:
        """Unlock the BT card using rfkill"""
        command = "rfkill unblock bluetooth"
        logging.info(f"Unlocking BT card using command: {command}")
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception as e:
            logging.error(f"Error unlocking BT card: {e}")

    async def start_pairing_mode(self):
        logging.info(
            f"Starting pairing mode and advertisement of {PT_SERVICE_UUID} and {DIS_SERVICE_UUID} for {PAIRING_TIME} seconds"
        )

        try:
            if await self.is_bt_card_blocked():
                logging.info("Bluetooth card is blocked, unlocking it...")
                await self.unlock_bt_card()

            self.bus = await get_message_bus()
            self.adapter = await Adapter.get_first(self.bus)

            # Give the adapter a moment to initialize
            await asyncio.sleep(2)

            # Make sure adapter is powered on
            powered = await self.adapter.get_powered()
            if not powered:
                logging.info("Powering on Bluetooth adapter...")
                await self.adapter.set_powered(True)
                await asyncio.sleep(2)

            self.agent = NoIoAgent()
            await self.agent.register(self.bus)

            self.advert = Advertisement(
                localName=get_bluetooth_server_name(),
                serviceUUIDs=[PT_SERVICE_UUID, DIS_SERVICE_UUID],
                appearance=APPEARANCE,
                timeout=PAIRING_TIME,
            )

            try:
                await self.advert.register(self.bus, self.adapter)
            except DBusError as e:
                if "Failed to register advertisement" in str(e):
                    logging.warning("Attempting to clean up existing advertisements...")
                    # Could add code here to force cleanup existing advertisements if needed
                    raise
                raise

            logging.info("Successfully started pairing mode")
            await asyncio.sleep(PAIRING_TIME)

        except Exception as e:
            logging.error(f"Error in pairing mode: {e}")
            raise
        finally:
            logging.info("Pairing time finished, cleaning up")
            await self.cleanup()


async def pairing_mode():
    manager = PairingManager()
    try:
        await manager.start_pairing_mode()
    except Exception as e:
        logging.error(f"Pairing mode failed: {e}")
        await manager.cleanup()


@click.command()
def main():
    asyncio.run(pairing_mode())


if __name__ == "__main__":
    main(prog_name="further-link-bluetooth-pairing")
