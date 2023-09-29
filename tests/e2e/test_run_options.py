import asyncio
import os
from datetime import datetime
from shutil import copy

import pytest

from further_link.util.message import create_message

from ..dirs import WORKING_DIRECTORY
from . import E2E_PATH
from .helpers import receive_data, wait_for_data
from .test_data.image import jpeg_pixel_b64


@pytest.mark.asyncio
async def test_run_code_script_with_directory(run_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message(
        "start", {"runner": "python3", "code": code, "directoryName": "my-dirname"}, "1"
    )
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_ws_client, "stdout", "output", day + "\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_run_code_relative_path(run_ws_client):
    copy("{}/test_data/print_date.py".format(E2E_PATH), WORKING_DIRECTORY)

    start_cmd = create_message(
        "start", {"runner": "python3", "path": "print_date.py"}, "1"
    )
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_ws_client, "stdout", "output", day + "\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
async def test_run_code_absolute_path(run_ws_client):
    start_cmd = create_message(
        "start",
        {"runner": "python3", "path": "{}/test_data/print_date.py".format(E2E_PATH)},
        "1",
    )
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_ws_client, "stdout", "output", day + "\n", 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")


import getpass
import pwd

current_user = getpass.getuser()
users = [
    p.pw_name
    for p in pwd.getpwall()
    if p.pw_shell != "/usr/sbin/nologin" and p.pw_name != current_user
]
user = users[-1] if len(users) and current_user == "root" else None


@pytest.mark.asyncio
@pytest.mark.skipif(user is None, reason="Cannot switch to a user")
@pytest.mark.parametrize("query_params", [{"user": user}])
async def test_run_as_user(run_ws_client_query):
    code = """\
#!/bin/bash
whoami
echo $LOGNAME
"""
    start_cmd = create_message("start", {"runner": "exec", "code": code}, "1")
    await run_ws_client_query.send_str(start_cmd)

    await receive_data(run_ws_client_query, "started", process="1")

    await wait_for_data(
        run_ws_client_query, "stdout", "output", f"{user}\n{user}\n", 0, "1"
    )

    await wait_for_data(run_ws_client_query, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
@pytest.mark.parametrize("query_params", [{"pty": "1"}])
async def test_input_pty(run_ws_client_query):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message("start", {"runner": "python3", "code": code}, "1")
    await run_ws_client_query.send_str(start_cmd)

    await receive_data(run_ws_client_query, "started", process="1")

    user_input = create_message("stdin", {"input": "hello\r"}, "1")
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(
        run_ws_client_query,
        "stdout",
        "output",
        "hello\r\nHUH?! SPEAK UP, SONNY!\r\n",
        0,
        "1",
    )

    user_input = create_message("stdin", {"input": "HEY GRANDMA\r"}, "1")
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(
        run_ws_client_query,
        "stdout",
        "output",
        "HEY GRANDMA\r\nNO, NOT SINCE 1930\r\n",
        0,
        "1",
    )

    user_input = create_message("stdin", {"input": "BYE\r"}, "1")
    await run_ws_client_query.send_str(user_input)

    await wait_for_data(run_ws_client_query, "stdout", "output", "BYE\r\n", 0, "1")

    await wait_for_data(run_ws_client_query, "stopped", "exitCode", 0, 0, "1")


@pytest.mark.asyncio
@pytest.mark.skipif("DISPLAY" not in os.environ, reason="requires X11 display")
async def test_novnc(run_ws_client):
    code = """\
import turtle
turtle.color('red', 'yellow')
from time import sleep
sleep(1) # activity monitor takes 1s to detect the window
"""
    start_cmd = create_message(
        "start",
        {"runner": "python3", "code": code, "novncOptions": {"enabled": True}},
        "1",
    )
    await run_ws_client.send_str(start_cmd)

    await receive_data(run_ws_client, "started", process="1")

    await wait_for_data(run_ws_client, "novnc", timeout=0, process="1")

    await wait_for_data(run_ws_client, "video", "output", jpeg_pixel_b64, 0, "1")

    await wait_for_data(run_ws_client, "stopped", "exitCode", 0, 0, "1")

    # TODO sleep seems to be required for clean activity monitor shutdown
    await asyncio.sleep(0.01)
