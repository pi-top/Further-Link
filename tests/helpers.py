from time import time
from concurrent.futures import TimeoutError

from src.util.message import parse_message


# this allows for the data to be split into multiple messages
async def receive_data(ws, channel, data_key=None, data_value=None,
                       process=''):
    received = ''
    # receive until we have enough data, or until return if non string data
    # receive has a timeout so if we don't get enough it will throw anyway
    while (not isinstance(data_value, str)) or len(received) < len(data_value):
        m_type, m_data, m_process = parse_message((await ws.receive()).data)

        assert m_process == process, f'{m_process} != {process}'
        assert m_type == channel, f'{m_type} != {channel}\ndata: {m_data}'

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
async def wait_for_data(ws, channel, data_key=None, data_value=None, timeout=0,
                        process=''):
    start_time = round(time())
    while timeout <= 0 or (round(time()) - start_time) <= timeout:
        try:
            message = await ws.receive()
            m_type, m_data, m_process = parse_message(message.data)

            assert m_process == process, f'{m_process} != {process}'
            assert m_type == channel, f'{m_type} != {channel}\ndata: {m_data}'

            # return if not looking for specific data
            if data_key is None:
                return

            assert(m_data.get(data_key, None) is not None)

            if data_value is None:
                return

            # m_data[data_key] should be at least the start of our data_value
            # equality check here for non string values
            value = m_data[data_key]
            assert(data_value == value or data_value.startswith(value))

            # return if it's all the data
            if data_value == value:
                return

            # use receive_data to gather rest
            remaining_data = data_value.replace(value, '', 1)
            return await receive_data(ws, channel, data_key, remaining_data)
        except TimeoutError:
            continue
    raise TimeoutError
