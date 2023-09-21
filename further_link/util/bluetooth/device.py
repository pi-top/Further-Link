import asyncio
import logging
from typing import Dict, Optional, Union

from bless import BlessGATTCharacteristic, BlessServer

from further_link.util.bluetooth.gatt import GattConfig
from further_link.util.bluetooth.messages import ChunkedMessage


def to_byte_array(value: str) -> bytearray:
    return bytearray(str(value), "utf-8")


def decode_value(value) -> str:
    if not isinstance(value, str):
        value = str(value, "utf-8")
    return value


class BluetoothDevice:
    def __init__(
        self,
        config: GattConfig,
    ):
        self.server: Optional[BlessServer] = None
        self.config = config
        self._partial_messages: Dict = {}

    async def start(self) -> None:
        logging.debug("Starting bluetooth server")
        loop = asyncio.get_running_loop()

        self.server = BlessServer(name=self.config.name, loop=loop)
        await asyncio.sleep(2)
        self.server.read_request_func = self._read_request
        self.server.write_request_func = self._write_request
        await self.server.add_gatt(self.config.tree)

        await self.server.start()
        logging.info("Bluetooth server is running")

    async def stop(self) -> None:
        if self.server:
            logging.info("Stopping bluetooth server")
            await self.server.stop()

    def _get_service_uuid(self, characteristic_uuid) -> str:
        if self.server is None:
            raise Exception("Bluetooth server not started")

        try:
            for service_uuid in self.server.services:
                service = self.server.services[service_uuid]
                if service.get_characteristic(characteristic_uuid):
                    return str(service.uuid)
        except KeyError:
            pass
        raise Exception(f"Unknown characteristic uuid: {characteristic_uuid}")

    def write_value(self, value: Union[str, bytearray], uuid: str) -> None:
        """Write a characteristic value, notifying subscribers"""
        if self.server is None:
            raise Exception("Bluetooth server not started")

        if isinstance(value, str):
            value = to_byte_array(value)

        logging.warning(f"Writing '{value}' to characteristic {uuid}")
        characteristic = self.server.get_characteristic(uuid)
        characteristic.value = value

        # Notify subscribers
        self.server.update_value(self._get_service_uuid(uuid), uuid)

    def read_value(self, uuid: str):
        if self.server is None:
            raise Exception("Bluetooth server not started")

        service_uuid = self._get_service_uuid(uuid)
        service = self.server.services.get(service_uuid)
        if service:
            char = service.get_characteristic(uuid)
            return self._read_request(char)

    def _read_request(self, characteristic: BlessGATTCharacteristic, **kwargs):
        logging.warning(f"Read request for characteristc {characteristic}")
        value = decode_value(characteristic.value)

        # callback on read requests will update the value of the characteristic before returning
        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("ReadHandler")
        )
        if callback and callable(callback):
            logging.warning(f"Executing ReadHandler callback for {characteristic.uuid}")
            try:
                value = str(callback())
                # TODO: handle long messages using ChunkedMessage
                self.write_value(value, characteristic.uuid)
            except Exception as e:
                logging.exception(f"Error executing callback: '{e}' - returning ''")
                value = ""

        logging.warning(
            f"Read request for characteristc {characteristic}; returning '{value}'"
        )

        return to_byte_array(value)

    def _write_request(
        self, characteristic: BlessGATTCharacteristic, value: bytearray, **kwargs
    ):
        logging.warning(
            f"Write request for characteristic {characteristic.uuid} with value '{value}'"
        )
        # if handling a 'ChunkedMessage', callback is executed only when the message is complete
        should_execute_callback = False

        if ChunkedMessage.is_start_message(value):
            self._partial_messages[characteristic.uuid] = ChunkedMessage()

        if self._partial_messages.get(characteristic.uuid):
            self._partial_messages[characteristic.uuid].append(value)
        else:
            should_execute_callback = True

        # update characteristic value in all cases
        self.write_value(value, characteristic.uuid)

        if ChunkedMessage.is_stop_message(value):
            value = self._partial_messages[characteristic.uuid].as_bytearray()
            del self._partial_messages[characteristic.uuid]
            should_execute_callback = True

        if not should_execute_callback:
            return

        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("WriteHandler")
        )
        if callable(callback):
            logging.warning(
                f"Executing WriteHandler callback for {characteristic.uuid}: {callback}"
            )

            async def run_callback():
                try:
                    await callback(self, characteristic.uuid, value)
                except Exception as e:
                    logging.exception(f"Error executing callback: {e}")

            asyncio.create_task(run_callback())
