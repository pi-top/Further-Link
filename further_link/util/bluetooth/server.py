import asyncio
import logging
from typing import Dict, Optional, Union

from bless import BlessGATTCharacteristic, BlessServer

from further_link.util.bluetooth.gatt import GattConfig
from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.messages.chunked_message import ChunkedMessage


def to_byte_array(value: str) -> bytearray:
    return bytearray(str(value), "utf-8")


def decode_value(value) -> str:
    if not isinstance(value, str):
        value = str(value, "utf-8")
    return value


class BluetoothServer:
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
            logging.debug("Stopping bluetooth server")
            await self.server.stop()

    def _get_service_uuid(self, characteristic_uuid: str) -> Optional[str]:
        if self.server is None:
            raise Exception("Bluetooth server not started")
        uuid = ""
        try:
            for service_uuid in self.server.services:
                service = self.server.services[service_uuid]
                if service.get_characteristic(characteristic_uuid):
                    uuid = str(service.uuid)
                    break
        except Exception:
            raise Exception(f"Unknown characteristic uuid: {characteristic_uuid}")

        return uuid

    def write_value(self, value: Union[str, bytearray], uuid: str) -> None:
        """Write a characteristic value, notifying subscribers"""
        if self.server is None:
            raise Exception("Bluetooth server not started")

        if isinstance(value, str):
            value = to_byte_array(value)

        logging.error(f"Writing '{value}' to characteristic {uuid}")
        characteristic = self.server.get_characteristic(uuid)
        characteristic.value = value

        # Notify subscribers
        self.server.update_value(self._get_service_uuid(uuid), uuid)

    def read_value(self, uuid: str) -> Optional[bytearray]:
        if self.server is None:
            raise Exception("Bluetooth server not started")

        value = bytearray()
        service_uuid = self._get_service_uuid(uuid)
        service = self.server.services.get(service_uuid)
        if service:
            char = service.get_characteristic(uuid)
            value = self._read_request(char)
        return value

    def _read_request(self, characteristic: BlessGATTCharacteristic, **kwargs):
        """method required by bless to handle read requests"""

        logging.debug(f"Read request for characteristc {characteristic}")
        value = decode_value(characteristic.value)

        # callback on read requests will update the value of the characteristic before returning
        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("ReadHandler")
        )
        if callback and callable(callback):
            logging.debug(f"Executing ReadHandler callback for {characteristic.uuid}")
            try:
                value = str(callback())
                # TODO: handle long messages using ChunkedMessage
                self.write_value(value, characteristic.uuid)
            except Exception as e:
                logging.exception(f"Error executing callback: '{e}' - returning ''")
                value = ""

        logging.debug(
            f"Read request for characteristc {characteristic}; returning '{value}'"
        )

        return to_byte_array(value)

    def _write_request(
        self, characteristic: BlessGATTCharacteristic, value: bytearray, **kwargs
    ):
        """method required by bless to handle write requests"""

        logging.debug(
            f"Write request for characteristic {characteristic.uuid} with value '{value}'"
        )
        # callback is executed only when a ChunkedMessage message is completely received
        should_execute_callback = False

        chunk = Chunk(value)
        if not self._partial_messages.get(chunk.id):
            self._partial_messages[chunk.id] = ChunkedMessage(chunk.id)

        try:
            self._partial_messages[chunk.id].append(chunk)
        except Exception as e:
            raise Exception(
                f"Error appending chunk {chunk} to message {self._partial_messages[chunk.id]}: {e}"
            )

        # update characteristic value in all cases
        self.write_value(value, characteristic.uuid)

        if self._partial_messages[chunk.id].is_complete():
            # get the complete message to execute callback
            value = self._partial_messages[chunk.id].as_bytearray()
            del self._partial_messages[chunk.id]
            should_execute_callback = True

        if not should_execute_callback:
            return

        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("WriteHandler")
        )
        if callable(callback):
            logging.error(
                f"Executing WriteHandler callback for {characteristic.uuid}: {callback} with {value}"
            )

            async def run_callback():
                try:
                    await callback(self, characteristic.uuid, value)
                except Exception as e:
                    logging.exception(f"Error executing callback: {e}")
                    raise

            # '_write_request' method is synchronous; callback is executed as a task
            asyncio.create_task(run_callback())
