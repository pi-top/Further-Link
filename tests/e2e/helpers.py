import asyncio
import json
from concurrent.futures import TimeoutError
from time import time

from further_link.util.bluetooth.messages.chunked_message import ChunkedMessage
from further_link.util.bluetooth.messages.format import PtMessageFormat
from further_link.util.message import parse_message


# this allows for the data to be split into multiple messages
async def receive_data(ws, channel, data_key=None, data_value=None, process=""):
    received = ""
    # receive until we have enough data, or until return if non string data
    # receive has a timeout so if we don't get enough it will throw anyway
    while (not isinstance(data_value, str)) or len(received) < len(data_value):
        m_type, m_data, m_process = parse_message((await ws.receive()).data)

        assert m_process == process, f"{m_process} != {process}, {m_type}, {m_data}"
        assert m_type == channel, f"{m_type} != {channel}\ndata: {m_data}"

        # return if not looking for specific data
        if data_key is None:
            return

        assert m_data.get(data_key) is not None, f"{m_data}"

        # if data_value is not string, it should all come in one go
        if not isinstance(data_value, str):
            assert data_value == m_data[data_key]
            return

        received += m_data[data_key]

    assert received == data_value


# this also allows for delay before receiving begins, beyond default timeout
async def wait_for_data(
    ws, channel, data_key=None, data_value=None, timeout=0, process=""
):
    start_time = round(time())
    while timeout <= 0 or (round(time()) - start_time) <= timeout:
        try:
            message = await ws.receive()
            m_type, m_data, m_process = parse_message(message.data)

            assert m_process == process, f"{m_process} != {process}"
            assert m_type == channel, f"{m_type} != {channel}\ndata: {m_data}"

            # return if not looking for specific data
            if data_key is None:
                return

            assert m_data.get(data_key) is not None, f"{m_data}"

            if data_value is None:
                return

            # m_data[data_key] should be at least the start of our data_value
            # equality check here for non string values
            value = m_data[data_key]
            assert data_value == value or data_value.startswith(value), value

            # return if it's all the data
            if data_value == value:
                return

            # use receive_data to gather rest
            remaining_data = data_value.replace(value, "", 1)
            return await receive_data(ws, channel, data_key, remaining_data)
        except (TimeoutError, asyncio.TimeoutError):
            continue
    raise TimeoutError


async def send_formatted_bluetooth_message(
    client, characteristic, message, assert_characteristic_value=True
):
    if not isinstance(message, str):
        message = json.dumps(message)
    chunked_message = ChunkedMessage.from_string(
        id=0, message=message, format=PtMessageFormat
    )

    for i in range(chunked_message.received_chunks):
        chunk = chunked_message.get_chunk(i)

        # send chunk to server
        client.server.write(characteristic, chunk.message)

        # read characteristic value and confirm it's the same message as the one sent
        if assert_characteristic_value:
            assert client.read_value(characteristic.uuid) == chunk.message


async def wait_until(condition, timeout=5.0):
    t = 0.0
    delta_t = 0.1
    while not condition() and t < timeout:
        await asyncio.sleep(delta_t)
        t += delta_t
    if t >= timeout:
        raise TimeoutError(f"Timed out waiting for condition {condition}")


async def wait_until_characteristic_value_endswith(
    client, characteristic_uuid, value, timeout=5
):
    def read_and_check():
        read = client.read_value(characteristic_uuid)
        return read.endswith(value)

    await wait_until(read_and_check, timeout)
