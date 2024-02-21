import asyncio
from datetime import datetime
from json import dumps, loads
from time import time

import pytest

from further_link.util.bluetooth.messages.chunk import Chunk
from further_link.util.bluetooth.uuids import (
    PT_CLIENTS_CHARACTERISTIC_UUID,
    PT_RUN_READ_CHARACTERISTIC_UUID,
    PT_RUN_WRITE_CHARACTERISTIC_UUID,
    PT_SERVICE_UUID,
)
from further_link.util.message import create_message

from .helpers import send_formatted_bluetooth_message, wait_until


def message_received(message: bytearray, messages: list):
    def _message_received():
        for msg in messages:
            if msg.endswith(message):
                return True
        return False

    return _message_received


@pytest.mark.asyncio
async def test_invalid_message(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)
    start_cmd = "not valid json"

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    # no message should be received
    await asyncio.sleep(1)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_fails_if_no_client_uuid_is_provided(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", None, {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    # no message should be received
    await asyncio.sleep(1)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_bad_message(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    # message is bad because it has no process id
    start_cmd = create_message("start", "1", {"runner": "python3", "code": ""})

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    await wait_until(lambda: len(messages) > 0)
    assert messages[0].endswith(
        b'{"type": "error", "data": {"message": "Bad message"}, "client": "1", "process": null}'
    )


@pytest.mark.asyncio
async def test_run_code_script(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""

    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    day = datetime.now().strftime("%A")
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{day}\r\n"},
            "client": "1",
            "process": "1",
        }
    )
    await wait_until(message_received(stdout_message.encode(), messages))

    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_run_shell(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    output = "i run shell commands"
    code = f"""\
echo {output}
"""

    start_cmd = create_message("start", "1", {"runner": "shell"}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    stdin_message = create_message("stdin", "1", {"input": code}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stdin_message)
    await wait_until(
        lambda: True in [output.encode() in message for message in messages]
    )

    stop_cmd = create_message("stop", "1", None, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)

    # really we expect a -15 exit code but this isn't necessarily a problem.
    # in buster, an extra 'exit' message is received and the process exits with code 0.
    # sleep for a bit to make sure test passes in buster and bullseye.
    await asyncio.sleep(1)
    await wait_until(lambda: len(messages) >= 3)
    chunk = Chunk(messages[-1])
    msg = loads(chunk.payload)
    assert msg["type"] == "stopped"
    assert msg["data"]["exitCode"] in (-9, 0)


@pytest.mark.asyncio
async def test_run_executable(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = """\
#!/bin/bash
date +%s # unix time in seconds
"""
    start_cmd = create_message("start", "1", {"runner": "exec", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    seconds = str(int(time()))
    stdout_message = dumps(
        {
            "type": "stdout",
            "data": {"output": f"{seconds}\r\n"},
            "client": "1",
            "process": "1",
        }
    )

    await wait_until(message_received(stdout_message.encode(), messages))
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_two_clients(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = "while True: pass"
    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    # number of clients is reported correctly
    clients_char = service.get_characteristic(PT_CLIENTS_CHARACTERISTIC_UUID)
    clients = clients_char.getter_func(service, {})
    chunk = Chunk(clients)
    assert chunk.message == clients
    assert chunk.payload == b"1"
    assert chunk.current_index == 0
    assert chunk.total_chunks == 1
    assert isinstance(chunk.id, int)
    assert chunk.id < 65536

    start_cmd = create_message("start", "2", {"runner": "python3", "code": code}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "2", "process": "1"}',
            messages,
        )
    )
    stop_cmd = create_message("stop", "2", None, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": -15}, "client": "2", "process": "1"}',
            messages,
        )
    )

    stop_cmd = create_message("stop", "1", None, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": -15}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_stop_early(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = "while True: pass"
    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)

    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    stop_cmd = create_message("stop", "1", None, "1")

    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": -15}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_bad_code(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    code = "i'm not valid python"
    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(lambda: len(messages) == 3)
    assert messages[0].endswith(
        b'{"type": "started", "data": null, "client": "1", "process": "1"}'
    )
    assert messages[2].endswith(
        b'{"type": "stopped", "data": {"exitCode": 1}, "client": "1", "process": "1"}'
    )

    chunk = Chunk(messages[1])
    content = loads(chunk.payload)
    lines = content["data"]["output"].split("\n")
    assert lines[0].startswith("  File")
    assert lines[1] == "    i'm not valid python\r"
    assert lines[2][-2:] == "^\r"
    assert lines[3] in (
        "SyntaxError: EOL while scanning string literal\r",
        "SyntaxError: unterminated string literal (detected at line 1)\r",
    )


@pytest.mark.asyncio
async def test_input(bluetooth_server):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    user_input = create_message("stdin", "1", {"input": "hello\n"}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, user_input)
    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "hello\\r\\nHUH?! SPEAK UP, SONNY!\\r\\n"}, "client": "1", "process": "1"}',
            messages,
        )
    )

    user_input = create_message("stdin", "1", {"input": "HEY GRANDMA\n"}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, user_input)
    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "HEY GRANDMA\\r\\nNO, NOT SINCE 1930\\r\\n"}, "client": "1", "process": "1"}',
            messages,
        )
    )

    user_input = create_message("stdin", "1", {"input": "BYE\n"}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, user_input)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_out_of_order_commands(bluetooth_server):
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    user_input = create_message("stdin", "1", {"input": "hello\n"}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, user_input)
    await wait_until(
        message_received(
            b'{"type": "error", "data": {"message": "Bad message"}, "client": "1", "process": null}',
            messages,
        )
    )
    messages.clear()

    stop_msg = create_message("stop", "1", None, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_msg)
    await wait_until(
        message_received(
            b'{"type": "error", "data": {"message": "Bad message"}, "client": "1", "process": null}',
            messages,
        )
    )
    messages.clear()

    # send start
    code = "while True: pass"
    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )
    messages.clear()

    # send start again
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "error", "data": {"message": "Bad message"}, "client": "1", "process": null}',
            messages,
        )
    )
    messages.clear()

    # send stop
    stop_cmd = create_message("stop", "1", None, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": -15}, "client": "1", "process": "1"}',
            messages,
        )
    )

    # send stop again
    await send_formatted_bluetooth_message(bluetooth_server, char, stop_cmd)
    await wait_until(
        message_received(
            b'{"type": "error", "data": {"message": "Bad message"}, "client": "1", "process": null}',
            messages,
        )
    )


@pytest.mark.asyncio
async def test_discard_old_input(bluetooth_server):
    code = 'print("hello world")'
    service = bluetooth_server.get_service(PT_SERVICE_UUID)
    char = service.get_characteristic(PT_RUN_WRITE_CHARACTERISTIC_UUID)

    messages = []
    service.get_characteristic(PT_RUN_READ_CHARACTERISTIC_UUID)._subscribe(
        lambda msg: messages.append(msg)
    )

    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    unterminated_input = create_message(
        "stdin", "1", {"input": "unterminated input"}, "1"
    )
    await send_formatted_bluetooth_message(bluetooth_server, char, unterminated_input)

    await asyncio.sleep(1)
    print(messages)

    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "hello world\\r\\n"}, "client": "1", "process": "1"}',
            messages,
        )
    )
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )

    messages.clear()

    code = "print(input())"
    start_cmd = create_message("start", "1", {"runner": "python3", "code": code}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, start_cmd)
    await wait_until(
        message_received(
            b'{"type": "started", "data": null, "client": "1", "process": "1"}',
            messages,
        )
    )

    user_input = create_message("stdin", "1", {"input": "hello\n"}, "1")
    await send_formatted_bluetooth_message(bluetooth_server, char, user_input)
    await wait_until(
        message_received(
            b'{"type": "stdout", "data": {"output": "hello\\r\\nhello\\r\\n"}, "client": "1", "process": "1"}',
            messages,
        )
    )
    await wait_until(
        message_received(
            b'{"type": "stopped", "data": {"exitCode": 0}, "client": "1", "process": "1"}',
            messages,
        )
    )
