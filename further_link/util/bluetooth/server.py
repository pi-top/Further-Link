import asyncio
import logging
from functools import lru_cache
from random import randint
from typing import Dict, Optional, Union

from bless import BlessGATTCharacteristic, BlessServer

from further_link.util.bluetooth.gatt import GattConfig
from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.messages.chunked_message import ChunkedMessage
from further_link.util.bluetooth.messages.format import PtMessageFormat


def to_bytearray(value: str):  # -> bytearray:
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
        self._received_partial_messages: Dict = {}
        self._send_partial_message: Dict = {}

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

    @lru_cache(maxsize=128)
    def _get_service_uuid(self, characteristic_uuid: str) -> str:
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

    async def write_value(self, value: Union[str, bytearray], uuid: str) -> None:
        """Write a characteristic value, notifying subscribers"""
        if self.server is None:
            raise Exception("Bluetooth server not started")

        if isinstance(value, str):
            value = to_bytearray(value)

        characteristic = self.server.get_characteristic(uuid)

        assert isinstance(value, bytearray)

        # Generate a random id
        id = randint(0, pow(2, 8 * PtMessageFormat.CHUNK_MESSAGE_ID_SIZE) - 1)
        chunked = ChunkedMessage.from_bytearray(id, value, PtMessageFormat)
        for i in range(chunked.total_chunks):
            chunked_message = chunked.get_chunk(i).message
            self._write_raw_value(chunked_message, characteristic)

    def _write_raw_value(
        self, value: Union[str, bytearray], characteristic: BlessGATTCharacteristic
    ) -> None:
        if self.server is None:
            raise Exception("Bluetooth server not started")

        logging.debug(f"Writing '{value}' to characteristic {characteristic.uuid}")

        # Write value
        characteristic.value = value

        # Notify subscribers
        self.server.update_value(
            self._get_service_uuid(characteristic.uuid), characteristic.uuid
        )

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
        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("ReadHandler")
        )

        chunked_message = self._send_partial_message.get(characteristic.uuid)
        value = characteristic.value
        if chunked_message:
            # if there's a chunked message for this uuid, respond with the next chunk.
            # use the current characteristic value to identify the last index that was sent
            latest_chunk_index = PtMessageFormat.get_chunk_current_index(
                characteristic.value
            )
            current_index = latest_chunk_index + 1

            value = chunked_message.get_chunk(current_index).message

            if current_index == chunked_message.total_chunks - 1:
                # cleanup when sending the last chunk
                del self._send_partial_message[characteristic.uuid]

            self._write_raw_value(value, characteristic)
        elif callback and callable(callback):
            # callback on read requests will update the value of the characteristic before returning
            logging.debug(f"Executing ReadHandler callback for {characteristic.uuid}")
            try:
                value = callback()
                if isinstance(value, str):
                    value = to_bytearray(value)
            except Exception as e:
                logging.exception(f"Error executing callback: '{e}' - returning ''")
                value = bytearray(b"")

            # Generate a random id
            id = randint(0, pow(2, 8 * PtMessageFormat.CHUNK_MESSAGE_ID_SIZE) - 1)
            chunked = ChunkedMessage.from_bytearray(id, value, PtMessageFormat)
            if chunked.total_chunks > 1:
                self._send_partial_message[characteristic.uuid] = chunked
            value = chunked.get_chunk(0).message
            self._write_raw_value(value, characteristic)

        logging.debug(
            f"Read request for characteristic {characteristic}; returning '{value}'"
        )
        return value

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
        if not self._received_partial_messages.get(chunk.id):
            self._received_partial_messages[chunk.id] = ChunkedMessage(chunk.id)

        try:
            self._received_partial_messages[chunk.id].append(chunk)
        except Exception as e:
            raise Exception(
                f"Error appending chunk {chunk} to message {self._received_partial_messages[chunk.id]}: {e}"
            )

        # update characteristic value in all cases
        self._write_raw_value(value, characteristic)

        if self._received_partial_messages[chunk.id].is_complete():
            value = self._received_partial_messages[chunk.id].as_bytearray()
            del self._received_partial_messages[chunk.id]
            should_execute_callback = True

        if not should_execute_callback:
            return

        callback = (
            self.config.tree.get(self._get_service_uuid(characteristic.uuid), {})
            .get(characteristic.uuid, {})
            .get("WriteHandler")
        )
        if callable(callback):
            logging.debug(
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
