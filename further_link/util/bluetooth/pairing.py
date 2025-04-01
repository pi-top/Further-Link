import asyncio
import logging

import click
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.agent import NoIoAgent
from bluez_peripheral.util import Adapter, get_message_bus

from further_link.util.bluetooth.utils import get_bluetooth_server_name
from further_link.util.bluetooth.uuids import PT_SERVICE_UUID

PAIRING_TIME = 60


async def is_bt_card_blocked() -> bool:
    """
    Check if the BT card is blocked by checking if the adapter is powered on.
    """
    cmd = "rfkill list bluetooth -o Soft -n"
    try:
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()
        return stdout.decode().strip() == "blocked"
    except Exception as e:
        logging.error(f"Error checking if BT card is blocked: {e}")
        return False

async def unlock_bt_card() -> None:
    """
    Unlock the BT card using rfkill
    """
    command = "rfkill unblock bluetooth"
    logging.info(f"Unlocking BT card using command: {command}")
    try:
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
    except Exception as e:
        logging.error(f"Error unlocking BT card: {e}")


async def pairing_mode():
    logging.info(
        f"Starting pairing mode and advertisement of {PT_SERVICE_UUID} for {PAIRING_TIME} seconds"
    )
    bus = await get_message_bus()
    adapter = await Adapter.get_first(bus)

    if await is_bt_card_blocked():
        logging.info("Bluetooth card is blocked, unlocking it...")
        await unlock_bt_card()

    agent = NoIoAgent()
    await agent.register(bus)

    advert = Advertisement(
        get_bluetooth_server_name(), [PT_SERVICE_UUID], 0, PAIRING_TIME
    )
    await advert.register(bus, adapter)

    await asyncio.sleep(PAIRING_TIME)

    logging.info("Pairing time finished, cleaning up")
    bus.disconnect()


@click.command()
def main():
    asyncio.run(pairing_mode())


if __name__ == "__main__":
    main(prog_name="further-link-bluetooth-pairing")
