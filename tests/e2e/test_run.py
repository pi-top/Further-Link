import asyncio
from datetime import datetime

import aiohttp
import pytest
from src.util.message import create_message, parse_message

from . import RUN_URL
from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_bad_message(run_ws_client):
    start_cmd = create_message("start", {"runner": "python3", "code": ""})
    await run_ws_client.send_str(start_cmd)

    await wait_for_data(run_ws_client, "error", "message", "Bad message")


@pytest.mark.asyncio
async def test_run_code_script(run_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_ws_client, "stdout", "output", day + "\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_run_two_scripts(run_ws_client):
    code1 = """\
from time import sleep
sleep(1)
print(1)
"""
    code2 = """\
print(2)
"""
    start_cmd = create_message("start", {"runner": "python3", "code": code1}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    start_cmd = create_message("start", {"runner": "python3", "code": code2}, "2")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="2")

    await wait_for_data(run_ws_client, "stdout", "output", "2\n", 0, "2")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "2")

    await wait_for_data(run_ws_client, "stdout", "output", "1\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_stop_early(run_ws_client):
    code = "while True: pass"
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    stop_cmd = create_message("stop", None, "1")
    await run_ws_client.send_str(stop_cmd)

    await wait_for_data(run_ws_client, "stopped", "exitCode", -15, 0, "1")


@pytest.mark.asyncio
async def test_bad_code(run_ws_client):
    code = "i'm not valid python"
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    await asyncio.sleep(0.1)  # wait for data
    message = await run_ws_client.receive()
    m_type, m_data, m_process = parse_message(message.data)
    assert m_type == "stderr"
    lines = m_data["output"].split("\n")
    assert lines[0].startswith("  File")
    assert lines[1] == "    i'm not valid python"
    assert lines[2] == "                       ^"
    assert lines[3] == "SyntaxError: EOL while scanning string literal"

    await wait_for_data(run_ws_client, "stopped", "exitCode", 1, 0, "1")


@pytest.mark.asyncio
async def test_input(run_ws_client):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    user_input = create_message("stdin", {"input": "hello\n"}, "1")
    await run_ws_client.send_str(user_input)

    await wait_for_data(
        run_ws_client, "stdout", "output", "HUH?! SPEAK UP, SONNY!\n", 0, "1"
    )

    user_input = create_message("stdin", {"input": "HEY GRANDMA\n"}, "1")
    await run_ws_client.send_str(user_input)

    await wait_for_data(
        run_ws_client, "stdout", "output", "NO, NOT SINCE 1930\n", 0, "1"
    )

    user_input = create_message("stdin", {"input": "BYE\n"}, "1")
    await run_ws_client.send_str(user_input)

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_two_clients(run_ws_client):
    async with aiohttp.ClientSession() as session2:
        async with session2.ws_connect(RUN_URL) as run_ws_client2:
            code = "while True: pass"
            start_cmd = create_message(
                "start", {"runner": "python3", "code": code}, "1"
            )
            await run_ws_client.send_str(start_cmd)

            await receive_data(run_ws_client, "started", process="1")

            await run_ws_client2.send_str(start_cmd)

            await receive_data(run_ws_client2, "started", process="1")

            stop_cmd = create_message("stop", None, "1")
            await run_ws_client.send_str(stop_cmd)

            await wait_for_data(run_ws_client, "stopped", "exitCode", -15, 100, "1")

            stop_cmd = create_message("stop", None, "1")
            await run_ws_client2.send_str(stop_cmd)

            await wait_for_data(run_ws_client2, "stopped", "exitCode", -15, 100, "1")


@pytest.mark.asyncio
async def test_out_of_order_commands(run_ws_client):
    # send input
    user_input = create_message("stdin", {"input": "hello\n"}, "1")
    await run_ws_client.send_str(user_input)

    # bad message
    await receive_data(run_ws_client, "error", "message", "Bad message")

    # send stop
    stop_cmd = create_message("stop", None, "1")
    await run_ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(run_ws_client, "error", "message", "Bad message")

    # send start
    code = "while True: pass"
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    # started
    await receive_data(run_ws_client, "started", process="1")

    # send start
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    # bad message
    await receive_data(run_ws_client, "error", "message", "Bad message")

    # send stop
    stop_cmd = create_message("stop", None, "1")
    await run_ws_client.send_str(stop_cmd)

    # stopped
    await wait_for_data(run_ws_client, "stopped", "exitCode", -15, 0, "1")

    # send stop
    stop_cmd = create_message("stop", None, "1")
    await run_ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(run_ws_client, "error", "message", "Bad message")


@pytest.mark.asyncio
async def test_discard_old_input(run_ws_client):
    code = 'print("hello world")'
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    unterminated_input = create_message("stdin", {"input": "unterminated input"}, "1")
    await run_ws_client.send_str(unterminated_input)

    await wait_for_data(run_ws_client, "stdout", "output", "hello world\n", 100, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")

    code = "print(input())"
    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    user_input = create_message("stdin", {"input": "hello\n"}, "1")
    await run_ws_client.send_str(user_input)

    await wait_for_data(run_ws_client, "stdout", "output", "hello\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")
