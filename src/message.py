import json


def create_message(msg_type, msg_data=None):
    return json.dumps({
        'type': msg_type,
        'data': msg_data
    })


def parse_message(message):
    try:
        msg = json.loads(message)
    except json.decoder.JSONDecodeError:
        raise BadMessage()

    msg_type = msg.get('type')
    msg_data = msg.get('data')

    msg_type = msg_type if isinstance(msg_type, str) else ''
    msg_data = msg_data if isinstance(msg_data, dict) else {}

    return msg_type, msg_data


class BadMessage(Exception):
    pass

class BadUpload(AssertionError):
    pass