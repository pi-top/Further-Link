from time import time
from concurrent.futures import TimeoutError

from src.message import parse_message


# this allows for the data to be split into multiple messages
async def receive_data(ws, channel, data_key=None, data_value=None):
    received = ''
    # receive until we have enough data, or until return if non string data
    # receive has a timeout so if we don't get enough it will throw anyway
    while (not isinstance(data_value, str)) or len(received) < len(data_value):
        m_type, m_data = parse_message((await ws.receive()).data)

        assert(m_type == channel)

        # return if not looking for specific data
        if data_key is None:
            return

        assert(m_data.get(data_key) is not None)

        # if data_value is not string, it should all come in one go
        if not isinstance(data_value, str):
            assert(data_value == m_data[data_key])
            return

        received += m_data[data_key]

    assert(received == data_value)


# this also allows for delay before receiving begins, beyond default timeout
async def wait_for_data(ws, channel, data_key=None, data_value=None, timeout=0):
    start_time = round(time())
    while timeout <= 0 or (round(time()) - start_time) <= timeout:
        try:
            m_type, m_data = parse_message((await ws.receive()).data)

            assert(m_type == channel)

            # return if not looking for specific data
            if data_key is None:
                return

            assert(m_data.get(data_key, False))

            # m_data should be at least the start of our data_value
            # equality check here for non string values
            assert(data_value == m_data or data_value.startswith(m_data))

            # return if it's all the data
            if data_value == m_data:
                return

            # use receive_data to gather rest
            remaining_data = data_value.replace(m_data, '', 1)
            return await receive_data(ws, channel, data_key, remaining_data)
        except TimeoutError:
            continue
    raise TimeoutError
