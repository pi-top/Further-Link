import asyncio
import logging
import os
from random import randint
from typing import Callable, Optional, Type, Union

from bluez_peripheral.gatt.characteristic import CharacteristicFlags, characteristic
from bluez_peripheral.gatt.service import Service

from further_link.endpoint.apt_version import apt_version_bt
from further_link.endpoint.run import bluetooth_run_handler
from further_link.endpoint.status import raw_status, raw_version
from further_link.endpoint.upload import bluetooth_upload
from further_link.util import state
from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.messages.chunked_message import ChunkedMessage
from further_link.util.bluetooth.messages.format import PtMessageFormat
from further_link.util.bluetooth.utils import find_object_with_uuid
from further_link.util.bluetooth.uuids import (
    PT_APT_VERSION_READ_CHARACTERISTIC_UUID,
    PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
    PT_CLIENTS_CHARACTERISTIC_UUID,
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
    PT_UPLOAD_READ_CHARACTERISTIC_UUID,
    PT_UPLOAD_WRITE_CHARACTERISTIC_UUID,
    PT_VERSION_CHARACTERISTIC_UUID,
    PT_WRITE_CHARACTERISTIC_UUID,
)


class SecureFlags:
    READ = CharacteristicFlags.ENCRYPT_READ
    WRITE = CharacteristicFlags.ENCRYPT_WRITE
    NOTIFY = CharacteristicFlags.NOTIFY


# Some OS doesn't support protected/secure characteristics
class NonSecureFlags:
    READ = CharacteristicFlags.READ
    WRITE = CharacteristicFlags.WRITE
    NOTIFY = CharacteristicFlags.NOTIFY


CharFlags: Union[Type[SecureFlags], Type[NonSecureFlags]] = SecureFlags
if os.environ.get("FURTHER_LINK_NO_BLUETOOTH_ENCRYPTION", "0").lower() in (
    "1",
    "true",
) or state.get("bluetooth", "encrypt", fallback="0").lower() in ("0", "false"):
    logging.info("Using unencrypted bluetooth characteristics")
    CharFlags = NonSecureFlags


def FurtherGattService():
    class _FurtherGattService(Service):
        def __init__(self):
            self._received_partial_messages = {}
            self._send_partial_message = {}
            self._client_run_managers = {}
            self._path = None
            self._registered = False
            super().__init__(PT_SERVICE_UUID, True)

        async def write_value(self, value, char):
            logging.debug(f"Writing value '{value}' to {char.uuid}")
            if isinstance(value, str):
                value = bytearray(value, "utf-8")

            # Generate a random id
            id = randint(0, pow(2, 8 * PtMessageFormat.CHUNK_MESSAGE_ID_SIZE) - 1)
            chunked = ChunkedMessage.from_bytearray(id, value, PtMessageFormat)
            for i in range(chunked.total_chunks):
                chunked_message = bytes(chunked.get_chunk(i).message)

                # Write to the characteristic
                char.value = chunked_message
                # Notify subscribers
                char.changed(chunked_message)

        @characteristic(PT_STATUS_CHARACTERISTIC_UUID, CharFlags.READ)
        def status(self, options):
            return self._read_request(PT_STATUS_CHARACTERISTIC_UUID, raw_status)

        @characteristic(PT_CLIENTS_CHARACTERISTIC_UUID, CharFlags.READ)
        def clients(self, options):
            def n_clients():
                return str(len(self._client_run_managers))

            return self._read_request(PT_CLIENTS_CHARACTERISTIC_UUID, n_clients)

        @characteristic(PT_WRITE_CHARACTERISTIC_UUID, CharFlags.WRITE)
        def write_test(self, options):
            pass

        @write_test.setter
        async def write_test(self, value, options):
            self._write_request(
                uuid=PT_WRITE_CHARACTERISTIC_UUID,
                value=value,
                callback=None,
            )

        @characteristic(PT_VERSION_CHARACTERISTIC_UUID, CharFlags.READ)
        def further_version(self, options):
            return self._read_request(PT_VERSION_CHARACTERISTIC_UUID, raw_version)

        # APT VERSION
        @characteristic(
            PT_APT_VERSION_READ_CHARACTERISTIC_UUID,
            CharFlags.READ | CharFlags.NOTIFY,
        )
        def apt_version_read(self, options):
            return self._read_request(PT_APT_VERSION_READ_CHARACTERISTIC_UUID)

        @characteristic(PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID, CharFlags.WRITE)
        def apt_version_write(self, options):
            pass

        @apt_version_write.setter
        async def apt_version_write(self, value, options):
            self._write_request(
                uuid=PT_APT_VERSION_WRITE_CHARACTERISTIC_UUID,
                value=value,
                callback=lambda message: apt_version_bt(
                    self, "", message, self.apt_version_read
                ),
            )

        # UPLOAD
        @characteristic(
            PT_UPLOAD_READ_CHARACTERISTIC_UUID,
            CharFlags.READ | CharFlags.NOTIFY,
        )
        def upload_read(self, options):
            pass

        @characteristic(PT_UPLOAD_WRITE_CHARACTERISTIC_UUID, CharFlags.WRITE)
        def upload_write(self, options):
            return self._read_request(PT_UPLOAD_WRITE_CHARACTERISTIC_UUID)

        @upload_write.setter
        async def upload_write(self, value, options):
            self._write_request(
                uuid=PT_UPLOAD_WRITE_CHARACTERISTIC_UUID,
                value=value,
                callback=lambda message: bluetooth_upload(
                    self, "", message, self.upload_read
                ),
            )

        # RUN
        @characteristic(
            PT_RUN_READ_CHARACTERISTIC_UUID,
            CharFlags.READ | CharFlags.NOTIFY,
        )
        def run_read(self, options):
            return self._read_request(PT_RUN_READ_CHARACTERISTIC_UUID)

        @characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID, CharFlags.WRITE)
        def run_write(self, options):
            pass

        @run_write.setter
        async def run_write(self, value, options):
            self._write_request(
                uuid=PT_RUN_WRITE_CHARACTERISTIC_UUID,
                value=value,
                callback=lambda message: bluetooth_run_handler(
                    self, message, self.run_read, self._client_run_managers
                ),
            )

        def _read_request(
            self, uuid: str, callback: Optional[Callable] = None, **kwargs
        ):
            logging.debug(f"Read request for characteristc {uuid}, {callback}")
            chunked_message = self._send_partial_message.get(uuid, {}).get(
                "chunked_message"
            )

            value = b""
            if chunked_message:
                # if there's a chunked message for this uuid, respond with the next chunk.
                sent_indexes = self._send_partial_message.get(uuid, {}).get("indexes")
                latest_chunk_index = PtMessageFormat.get_chunk_current_index(
                    chunked_message.get_chunk(max(sent_indexes)).message
                )
                current_index = latest_chunk_index + 1
                self._send_partial_message[uuid]["indexes"].append(current_index)

                value = chunked_message.get_chunk(current_index).message

                if current_index == chunked_message.total_chunks - 1:
                    # cleanup when sending the last chunk
                    del self._send_partial_message[uuid]

            elif callable(callback):
                # callback on read requests will update the value of the characteristic before returning
                logging.debug(f"Executing ReadHandler callback for {uuid}")
                try:
                    value = callback()
                    if isinstance(value, str):
                        value = bytearray(value, "utf-8")
                except Exception as e:
                    logging.exception(f"Error executing callback: '{e}' - returning ''")
                    value = bytearray(b"")

                if not isinstance(value, bytearray):
                    raise Exception(
                        f"Callback must return a bytearray, but returned a {type(value)}"
                    )

                # Generate a random id
                id = randint(0, pow(2, 8 * PtMessageFormat.CHUNK_MESSAGE_ID_SIZE) - 1)
                chunked = ChunkedMessage.from_bytearray(id, value, PtMessageFormat)
                if chunked.total_chunks > 1:
                    self._send_partial_message[uuid] = {}
                    self._send_partial_message[uuid]["chunked_message"] = chunked
                    self._send_partial_message[uuid]["indexes"] = [0]
                value = chunked.get_chunk(0).message

            logging.debug(
                f"Read request for characteristic {uuid}; returning '{value!r}'"
            )
            return value

        def _write_request(
            self, uuid: str, value: bytearray, callback: Optional[Callable], **kwargs
        ):
            logging.debug(
                f"Write request for characteristic {uuid} with value '{value}'"
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

            if self._received_partial_messages[chunk.id].is_complete():
                value = self._received_partial_messages[chunk.id].as_bytearray()
                del self._received_partial_messages[chunk.id]
                should_execute_callback = True

            if not should_execute_callback:
                return

            if callable(callback):
                logging.debug(
                    f"Executing WriteHandler callback for {uuid}: {callback} with {value}"
                )

                async def run_callback():
                    try:
                        await callback(value)
                    except Exception as e:
                        logging.exception(f"Error executing callback: {e}")
                        raise

                asyncio.create_task(run_callback())

        def get_characteristic(self, uuid: str) -> Optional[characteristic]:
            return find_object_with_uuid(self._characteristics, uuid)

        def set_path(self, path):
            self._path = path

        def cleanup(self):
            if self._registered:
                # Unregister from D-Bus
                self.unregister()  # Implement this method to remove from D-Bus
                self._registered = False

    return _FurtherGattService()
