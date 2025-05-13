import logging
from asyncio import sleep

from bluez_peripheral.util import Adapter, get_message_bus

from further_link.util.bluetooth.utils import is_bt_card_blocked, unlock_bt_card


class BluetoothDevice:
    def __init__(self):
        self.bus = None
        self.adapter = None

    @classmethod
    async def create(cls):
        device = cls()
        await device.initialize()
        return device

    async def initialize(self):
        if await is_bt_card_blocked():
            logging.info("Bluetooth card is blocked, unlocking it...")
            await unlock_bt_card()

        self.bus = await get_message_bus()
        self.adapter = await Adapter.get_first(self.bus)

        # Give the adapter a moment to initialize
        await sleep(1)

        # Make sure adapter is powered on
        powered = await self.adapter.get_powered()
        if not powered:
            logging.info("Powering on Bluetooth adapter...")
            await self.adapter.set_powered(True)
            await sleep(1)

    async def cleanup(self):
        if self.bus:
            self.bus.disconnect()
