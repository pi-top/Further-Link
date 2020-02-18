import json


def create_message(type, data=None):
    return json.dumps({
        'type': type,
        'data': data
    })


def parse_message(message):
    try:
        m = json.loads(message)
    except json.decoder.JSONDecodeError:
        raise BadMessage()

    m_type = m.get('type')
    m_data = m.get('data')

    m_type = m_type if isinstance(m_type, str) else ''
    m_data = m_data if isinstance(m_data, dict) else {}

    return m_type, m_data


class BadMessage(Exception):
    pass
