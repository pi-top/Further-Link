import json


class BadMessage(Exception):
    pass


def create_message(msg_type, msg_data=None, msg_process=''):
    return json.dumps({
        'type': msg_type,
        'data': msg_data,
        'process': msg_process
    })


def parse_message(message):
    try:
        msg = json.loads(message)
    except json.decoder.JSONDecodeError:
        raise BadMessage()

    msg_type = msg.get('type')
    msg_data = msg.get('data')
    msg_process = msg.get('process')

    msg_type = msg_type if isinstance(msg_type, str) else ''
    msg_data = msg_data if isinstance(msg_data, dict) else {}
    msg_process = msg_process if isinstance(msg_process, str) else ''

    return msg_type, msg_data, msg_process
