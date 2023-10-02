import json

from further_link.util.bluetooth.gatt import (
    PT_SERVICE_UUID,
    PT_STATUS_CHARACTERISTIC_UUID,
)
from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.messages.chunked_message import ChunkedMessage
from further_link.util.bluetooth.messages.format import PtMessageFormat
from further_link.util.bluetooth.messages.message import Message

from .test_data.text_data import lorem_ipsum_100
from .test_data.upload_data import directory


def test_message_class():
    # class constructor with empty data
    message = Message()
    assert message.size == 0
    assert message.as_bytearray() == bytearray()
    assert message.as_string() == ""

    # append data
    message.append(bytearray(b"test"))
    assert message.size == 4
    assert message.as_bytearray() == bytearray(b"test")
    assert message.as_string() == "test"

    # constructor with data
    message = Message(bytearray(b"test"))
    assert message.size == 4
    assert message.as_bytearray() == bytearray(b"test")
    assert message.as_string() == "test"

    # class instantiation from a string
    message = Message.from_string("test")
    assert message.size == 4
    assert message.as_bytearray() == bytearray(b"test")
    assert message.as_string() == "test"


def test_ptformat_class():
    # create a message
    message = Message.from_string("test")

    # create a PtMessageFormat instance
    pt_format = PtMessageFormat()

    id = 10
    end_index = 34
    curr_index = 2
    data = b"this-is-a-message"

    # create a formatted message
    formatted_message = pt_format.create_message(
        id=id, current_index=curr_index, total_chunks=end_index + 1, data=data
    )

    # test the formatted message
    assert pt_format.get_id(formatted_message) == id
    assert pt_format.get_chunk_current_index(formatted_message) == curr_index
    assert pt_format.get_chunk_end_index(formatted_message) == end_index
    assert pt_format.get_payload(formatted_message) == data
    assert (
        pt_format.get_complete_message_size(formatted_message)
        == pt_format.DATA_SIZE * end_index
    )
    assert pt_format.get_number_of_chunks_for_message(message) == 1


def test_chunk_class():
    id = 33
    end_index = 500
    curr_index = 50
    data = b"this-is-the-message"

    formatted_message = bytearray(
        int.to_bytes(id, 2, byteorder="big")
        + int.to_bytes(end_index, 3, byteorder="big")
        + int.to_bytes(curr_index, 3, byteorder="big")
        + data
    )

    chunk = Chunk(formatted_message, PtMessageFormat)
    assert chunk.message == formatted_message
    assert chunk.format == PtMessageFormat


def test_chunkedmessage_from_message_one_chunk():
    # create a message shorter than format.DATA_SIZE that requires only 1 chunk of data
    message_bytes = b"this-is-a-test-message"
    m = Message(bytearray(message_bytes))

    chunked = ChunkedMessage.from_message(0, m, PtMessageFormat)
    assert chunked.received_chunks == 1
    assert chunked.get_chunk(0).payload == bytearray(message_bytes)
    assert chunked.as_bytearray() == bytearray(message_bytes)

    # message is the same as the original
    assert chunked.as_string() == message_bytes.decode()
    assert chunked.as_bytearray() == message_bytes


def test_chunkedmessage_from_message_multiple_chunks():
    # create a longer message to force more than 1 chunk of data
    m = Message.from_string(json.dumps(directory))
    chunked = ChunkedMessage.from_message(0, m, PtMessageFormat)

    assert chunked.received_chunks == 2
    for i in range(chunked.received_chunks):
        assert chunked.get_chunk(i).payload == bytearray(
            m.as_bytearray()[
                i * PtMessageFormat.DATA_SIZE : PtMessageFormat.DATA_SIZE * (i + 1)
            ]
        )

    # message is the same as the original
    assert chunked.as_string() == json.dumps(directory)


def test_chunkedmessage_append():
    m = Message.from_string(lorem_ipsum_100)

    # create a ChunkedMessage to simulate the client sending a long message in chunks
    client_chunks = ChunkedMessage.from_message(1, m, PtMessageFormat)

    # create an empty ChunkedMessage
    received_message = ChunkedMessage(1)

    # incrementally append client Chunks to the empty ChunkedMessage
    for i in range(client_chunks.total_chunks):
        received_message.append(client_chunks.get_chunk(i))

        # 'received_chunks' should be incremented by 1 each time
        assert received_message.received_chunks == i + 1

        # 'total_chunks' is retrieved from the first chunk and shouldn't change
        assert received_message.total_chunks == client_chunks.total_chunks

        # 'received_chunks' should be incremented by 1 each time
        assert (
            received_message.get_chunk(i).payload == client_chunks.get_chunk(i).payload
        )

        # partial message should be the same as the original
        assert (
            received_message.as_string()
            == client_chunks.as_string()[: (i + 1) * PtMessageFormat.DATA_SIZE]
        )

        # is_complete should return False until all chunks are received
        assert received_message.is_complete() == bool(
            i == client_chunks.total_chunks - 1
        )

    # received message is the same as the original
    assert received_message.as_string() == client_chunks.as_string()
    assert received_message.as_bytearray() == client_chunks.as_bytearray()


def test_server_sends_chunked_message(mocker, bluetooth_client):
    # server responds with a chunked message.
    # client can read and get sequential chunks of the message

    char = bluetooth_client.server.get_service(PT_SERVICE_UUID).get_characteristic(
        PT_STATUS_CHARACTERISTIC_UUID
    )

    # mock "status" characteristic read handler to return a very long message
    gatt_char = bluetooth_client.config.tree.get(
        bluetooth_client._get_service_uuid(char.uuid), {}
    ).get(char.uuid, {})
    gatt_char["ReadHandler"] = lambda: lorem_ipsum_100

    # chunks provide information about message size
    chunk = Chunk(bluetooth_client._read_request(char))
    end_index = chunk.total_chunks - 1
    current_index = 0
    chunked = ChunkedMessage.from_chunk(chunk, PtMessageFormat)

    while current_index < end_index:
        chunk = Chunk(bluetooth_client._read_request(char))
        chunked.append(chunk)
        current_index = chunk.current_index

    assert chunked.as_string() == lorem_ipsum_100
