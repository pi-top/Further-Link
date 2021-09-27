import asyncio
import os
from datetime import datetime
from shutil import copy

import aiohttp
import pytest

from further_link import __version__
from further_link.util.message import create_message, parse_message

from ..dirs import WORKING_DIRECTORY
from . import E2E_PATH, RUN_PY_URL
from .helpers import receive_data, wait_for_data


@pytest.mark.asyncio
async def test_bad_message(run_py_ws_client):
    start_cmd = create_message("start")
    await run_py_ws_client.send_str(start_cmd)

    await wait_for_data(run_py_ws_client, "error", "message", "Bad message")


@pytest.mark.asyncio
async def test_run_code_script(run_py_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_py_ws_client, "stdout", "output", day + "\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_run_code_script_with_directory(run_py_ws_client):
    code = """\
from datetime import datetime
print(datetime.now().strftime("%A"))
"""
    start_cmd = create_message(
        "start", {"sourceScript": code, "directoryName": "my-dirname"}
    )
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_py_ws_client, "stdout", "output", day + "\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_run_code_relative_path(run_py_ws_client):
    copy("{}/test_data/print_date.py".format(E2E_PATH), WORKING_DIRECTORY)

    start_cmd = create_message("start", {"sourcePath": "print_date.py"})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_py_ws_client, "stdout", "output", day + "\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_run_code_absolute_path(run_py_ws_client):
    start_cmd = create_message(
        "start", {"sourcePath": "{}/test_data/print_date.py".format(E2E_PATH)}
    )
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    day = datetime.now().strftime("%A")
    await wait_for_data(run_py_ws_client, "stdout", "output", day + "\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("query_params", [{"user": "root"}])
@pytest.mark.skip(reason="Won't work in CI due to old sudo version")
async def test_run_as_user(run_py_ws_client_query):
    # This test assumes non-root user with nopasswd sudo access...
    code = "import getpass\nprint(getpass.getuser())"
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client_query.send_str(start_cmd)

    await receive_data(run_py_ws_client_query, "started")

    await wait_for_data(run_py_ws_client_query, "stdout", "output", "root\n")

    await wait_for_data(run_py_ws_client_query, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_stop_early(run_py_ws_client):
    code = "while True: pass"
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    stop_cmd = create_message("stop")
    await run_py_ws_client.send_str(stop_cmd)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", -15)


@pytest.mark.asyncio
async def test_bad_code(run_py_ws_client):
    code = "i'm not valid python"
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    await asyncio.sleep(0.1)  # wait for data
    message = await run_py_ws_client.receive()
    m_type, m_data, m_process = parse_message(message.data)
    assert m_type == "stderr"
    lines = m_data["output"].split("\n")
    assert lines[0].startswith("  File")
    assert lines[1] == "    i'm not valid python"
    assert lines[2] == "                       ^"
    assert lines[3] == "SyntaxError: EOL while scanning string literal"

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 1)


@pytest.mark.asyncio
async def test_input(run_py_ws_client):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    user_input = create_message("stdin", {"input": "hello\n"})
    await run_py_ws_client.send_str(user_input)

    await wait_for_data(
        run_py_ws_client, "stdout", "output", "HUH?! SPEAK UP, SONNY!\n"
    )

    user_input = create_message("stdin", {"input": "HEY GRANDMA\n"})
    await run_py_ws_client.send_str(user_input)

    await wait_for_data(run_py_ws_client, "stdout", "output", "NO, NOT SINCE 1930\n")

    user_input = create_message("stdin", {"input": "BYE\n"})
    await run_py_ws_client.send_str(user_input)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("query_params", [{"pty": "1"}])
async def test_input_pty(run_py_ws_client_query):
    code = """s = input()
while "BYE" != s:
    print(["HUH?! SPEAK UP, SONNY!","NO, NOT SINCE 1930"][s.isupper()])
    s = input()"""

    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client_query.send_str(start_cmd)

    await receive_data(run_py_ws_client_query, "started")

    user_input = create_message("stdin", {"input": "hello\r"})
    await run_py_ws_client_query.send_str(user_input)

    await wait_for_data(
        run_py_ws_client_query,
        "stdout",
        "output",
        "hello\r\nHUH?! SPEAK UP, SONNY!\r\n",
    )

    user_input = create_message("stdin", {"input": "HEY GRANDMA\r"})
    await run_py_ws_client_query.send_str(user_input)

    await wait_for_data(
        run_py_ws_client_query,
        "stdout",
        "output",
        "HEY GRANDMA\r\nNO, NOT SINCE 1930\r\n",
    )

    user_input = create_message("stdin", {"input": "BYE\r"})
    await run_py_ws_client_query.send_str(user_input)

    await wait_for_data(run_py_ws_client_query, "stdout", "output", "BYE\r\n")

    await wait_for_data(run_py_ws_client_query, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_two_clients(run_py_ws_client):
    async with aiohttp.ClientSession() as session2:
        async with session2.ws_connect(RUN_PY_URL) as run_py_ws_client2:
            code = "while True: pass"
            start_cmd = create_message("start", {"sourceScript": code})
            await run_py_ws_client.send_str(start_cmd)

            await receive_data(run_py_ws_client, "started")

            await run_py_ws_client2.send_str(start_cmd)

            await receive_data(run_py_ws_client2, "started")

            stop_cmd = create_message("stop")
            await run_py_ws_client.send_str(stop_cmd)

            await wait_for_data(run_py_ws_client, "stopped", "exitCode", -15, 100)

            stop_cmd = create_message("stop")
            await run_py_ws_client2.send_str(stop_cmd)

            await wait_for_data(run_py_ws_client2, "stopped", "exitCode", -15, 100)


@pytest.mark.asyncio
async def test_out_of_order_commands(run_py_ws_client):
    # send input
    user_input = create_message("stdin", {"input": "hello\n"})
    await run_py_ws_client.send_str(user_input)

    # bad message
    await receive_data(run_py_ws_client, "error", "message", "Bad message")

    # send stop
    stop_cmd = create_message("stop")
    await run_py_ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(run_py_ws_client, "error", "message", "Bad message")

    # send start
    code = "while True: pass"
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    # started
    await receive_data(run_py_ws_client, "started")

    # send start
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    # bad message
    await receive_data(run_py_ws_client, "error", "message", "Bad message")

    # send stop
    stop_cmd = create_message("stop")
    await run_py_ws_client.send_str(stop_cmd)

    # stopped
    await wait_for_data(run_py_ws_client, "stopped", "exitCode", -15)

    # send stop
    stop_cmd = create_message("stop")
    await run_py_ws_client.send_str(stop_cmd)

    # bad message
    await receive_data(run_py_ws_client, "error", "message", "Bad message")


@pytest.mark.asyncio
async def test_discard_old_input(run_py_ws_client):
    code = 'print("hello world")'
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    unterminated_input = create_message("stdin", {"input": "unterminated input"})
    await run_py_ws_client.send_str(unterminated_input)

    await wait_for_data(run_py_ws_client, "stdout", "output", "hello world\n", 100)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)

    code = "print(input())"
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    user_input = create_message("stdin", {"input": "hello\n"})
    await run_py_ws_client.send_str(user_input)

    await wait_for_data(run_py_ws_client, "stdout", "output", "hello\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_use_lib(run_py_ws_client):
    code = """\
from further_link import __version__
print(__version__)
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "stdout", "output", f"{__version__}\n")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
@pytest.mark.skipif("DISPLAY" not in os.environ, reason="requires UI")
async def test_use_display(run_py_ws_client):
    code = """\
from turtle import color
color('red')
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await receive_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0, 5000)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Temporarily disabled - to be fixed")
async def test_keyevent(run_py_ws_client):
    code = """\
from further_link import KeyboardButton
from signal import pause
a = KeyboardButton('a')
b = KeyboardButton('b')
a.when_pressed = lambda: print('a pressed')
b.when_released = lambda: print('b released')
pause()
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await wait_for_data(run_py_ws_client, "started")
    await wait_for_data(run_py_ws_client, "keylisten", "output", "a")
    await wait_for_data(run_py_ws_client, "keylisten", "output", "b")

    await run_py_ws_client.send_str(
        create_message("keyevent", {"key": "a", "event": "keydown"})
    )

    await wait_for_data(run_py_ws_client, "stdout", "output", "a pressed\n")

    await run_py_ws_client.send_str(
        create_message("keyevent", {"key": "b", "event": "keyup"})
    )

    await wait_for_data(run_py_ws_client, "stdout", "output", "b released\n")

    await run_py_ws_client.send_str(create_message("stop"))

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", -15)


jpeg_pixel_b64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP//Z"  # noqa: E501


@pytest.mark.asyncio
async def test_send_image_pil(run_py_ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await wait_for_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "video", "output", jpeg_pixel_b64)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_send_image_opencv(run_py_ws_client):
    code = """\
from numpy import array
from further_link import send_image
from PIL.Image import effect_noise
send_image(array(effect_noise((1, 1), 0)))
"""
    start_cmd = create_message("start", {"sourceScript": code})
    await run_py_ws_client.send_str(start_cmd)

    await wait_for_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "video", "output", jpeg_pixel_b64)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)


@pytest.mark.asyncio
async def test_send_image_with_directory(run_py_ws_client):
    code = """\
from further_link import send_image
from PIL.Image import effect_noise
send_image(effect_noise((1, 1), 0))
"""
    start_cmd = create_message(
        "start", {"sourceScript": code, "directoryName": "my-dirname"}
    )
    await run_py_ws_client.send_str(start_cmd)

    await wait_for_data(run_py_ws_client, "started")

    await wait_for_data(run_py_ws_client, "video", "output", jpeg_pixel_b64)

    await wait_for_data(run_py_ws_client, "stopped", "exitCode", 0)
