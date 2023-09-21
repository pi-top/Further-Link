import json
import re
from typing import Dict


def bytearray_to_dict(message: bytearray) -> Dict:
    message_str = message.decode()

    # remove trailing commas
    message_str = re.sub(",[ \t\r\n]+}", "}", message_str)
    message_str = re.sub(",[ \t\r\n]+]", "]", message_str)

    return json.loads(message_str)
