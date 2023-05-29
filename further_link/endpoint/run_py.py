import asyncio
import logging

from aiohttp import web

from ..runner.run_py_process_handler import InvalidOperation, RunPyProcessHandler
from ..util.message import BadMessage, create_message, parse_message
from ..util.upload import BadUpload, directory_is_valid, do_upload


async def handle_message(message, process_handler, socket, bluetooth):
    async def send(message):
        await socket.send_str(message)
        await bluetooth.send(message)

    m_type, m_data, m_process = parse_message(message)

    if (
        m_type == "start"
        and "sourceScript" in m_data
        and isinstance(m_data.get("sourceScript"), str)
    ):
        path = (
            m_data.get("directoryName")
            if (
                "directoryName" in m_data
                and isinstance(m_data.get("directoryName"), str)
                and len(m_data.get("directoryName")) > 0
            )
            else None
        )
        await process_handler.start(
            script=m_data["sourceScript"],
            path=path,
        )

    elif (
        m_type == "start"
        and "sourcePath" in m_data
        and isinstance(m_data.get("sourcePath"), str)
        and len(m_data.get("sourcePath")) > 0
    ):
        await process_handler.start(path=m_data["sourcePath"])

    elif (
        m_type == "upload"
        and "directory" in m_data
        and directory_is_valid(m_data.get("directory"))
    ):
        await do_upload(
            m_data.get("directory"), process_handler.work_dir, m_data.get("user")
        )
        await send(create_message("uploaded"))

    elif (
        m_type == "stdin" and "input" in m_data and isinstance(m_data.get("input"), str)
    ):
        await process_handler.send_input(m_data["input"])

    elif m_type == "ping":
        await send(create_message("pong"))

    elif m_type == "stop":
        process_handler.stop()

    elif (
        m_type == "keyevent"
        and "key" in m_data
        and isinstance(m_data.get("key"), str)
        and "event" in m_data
        and isinstance(m_data.get("event"), str)
    ):
        await process_handler.send_key_event(m_data["key"], m_data["event"])

    else:
        raise BadMessage()


async def run_py(request):
    query_params = request.query
    user = query_params.get("user", None)
    pty = query_params.get("pty", "").lower() in ["1", "true"]

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    bluetooth = request.app["bluetooth_device"]

    async def send(message):
        await socket.send_str(message)
        bluetooth.send(message)

    async def on_start():
        await send(create_message("started"))
        logging.info(f"{process_handler.id} Started")

    async def on_stop(exit_code):
        try:
            await send(create_message("stopped", {"exitCode": exit_code}))
        except ConnectionResetError:
            pass  # already disconnected
        logging.info(f"{process_handler.id} Stopped")

    async def on_output(channel, output):
        logging.debug(f"{process_handler.id} Sending Output {channel} {output}")
        await send(create_message(channel, {"output": output}))

    process_handler = RunPyProcessHandler(user=user, pty=pty)
    process_handler.on_start = on_start
    process_handler.on_stop = on_stop
    process_handler.on_output = on_output
    logging.info(f"{process_handler.id} New connection")

    async def handle(message, process_handler):
        logging.debug(f"{process_handler.id} Received Message {message.data}")
        try:
            await handle_message(message.data, process_handler, socket, bluetooth)

        except BadUpload:
            logging.exception(f"{process_handler.id} Bad Upload")
            await send(create_message("error", {"message": "Bad upload"}))

        except (BadMessage, InvalidOperation):
            logging.exception(f"{process_handler.id} Bad Message")
            await send(create_message("error", {"message": "Bad message"}))

        except Exception:
            logging.exception(f"{process_handler.id} Message Exception")
            await send(create_message("error", {"message": "Message Exception"}))

    try:
        async for message in socket:
            await handle(message, process_handler)

        while bluetooth.has_messages():
            await handle(bluetooth.read(), process_handler)
    except asyncio.CancelledError:
        pass
    finally:
        await socket.close()

    logging.info(f"{process_handler.id} Closed connection")
    if process_handler.is_running():
        process_handler.stop()

    return socket
