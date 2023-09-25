import asyncio
import logging
from typing import Callable, Dict

from aiohttp import web
from pt_web_vnc.connection_details import VncConnectionDetails

from ..runner.exec_process_handler import ExecProcessHandler
from ..runner.process_handler import InvalidOperation
from ..runner.py_process_handler import PyProcessHandler
from ..runner.shell_process_handler import ShellProcessHandler
from ..util.bluetooth.utils import bytearray_to_dict
from ..util.message import BadMessage, create_message, parse_message
from ..util.user_config import default_user, get_temp_dir


class RunManager:
    def __init__(self, send_func: Callable, user=None, pty=False):
        self.send_func = send_func
        self.user = default_user() if user is None else user
        self.pty = pty

        self.id = str(id(self))
        self.process_handlers: Dict = {}
        self.handler_classes = {
            "exec": ExecProcessHandler,
            "python3": PyProcessHandler,
            "shell": ShellProcessHandler,
        }

    async def stop(self):
        # the dictionary will be mutated so use list to make a copy
        for p in list(self.process_handlers.values()):
            try:
                await p.stop()
            except InvalidOperation:
                pass

    async def send(self, type, data=None, process_id=None):
        await self.send_func(create_message(type, data, process_id))

    async def handle_message(self, message):
        try:
            m_type, m_data, m_process = parse_message(message)

            process_handler = self.process_handlers.get(m_process)

            if m_type == "ping":
                await self.send("pong")

            elif (
                m_type == "start"
                and not process_handler
                and m_process
                and isinstance(m_data.get("runner"), str)
            ):
                code = m_data.get("code")
                code = code if isinstance(code, str) else None
                path = m_data.get("path")
                path = path if isinstance(path, str) and len(path) else get_temp_dir()
                novncOptions = m_data.get("novncOptions")
                novncOptions = (
                    novncOptions
                    if (
                        isinstance(novncOptions, dict)
                        and isinstance(novncOptions.get("enabled"), bool)
                    )
                    else {"enabled": False}
                )
                await self.add_handler(
                    m_process, m_data["runner"], path, code, novncOptions
                )

            elif (
                m_type == "stdin"
                and process_handler
                and isinstance(m_data.get("input"), str)
            ):
                await process_handler.send_input(m_data["input"])

            elif (
                m_type == "resize"
                and process_handler
                and isinstance(m_data.get("rows"), int)
                and isinstance(m_data.get("cols"), int)
            ):
                await process_handler.resize_pty(m_data["rows"], m_data["cols"])

            elif m_type == "stop" and process_handler:
                await process_handler.stop()

            elif (
                m_type == "keyevent"
                and process_handler
                and isinstance(m_data.get("key"), str)
                and isinstance(m_data.get("event"), str)
            ):
                await process_handler.send_key_event(m_data["key"], m_data["event"])

            else:
                raise BadMessage()

        except (BadMessage, InvalidOperation):
            logging.exception(f"{self.id} Bad Message")
            await self.send("error", {"message": "Bad message"})

        except Exception as e:
            logging.exception(f"{self.id} Message Exception: {e}")
            await self.send("error", {"message": "Message Exception"})

    async def add_handler(self, process_id, runner, path, code, novncOptions):
        try:
            handler_class = self.handler_classes[runner]
        except KeyError:
            raise BadMessage("Start command runner invalid") from None

        async def on_start():
            await self.send("started", None, process_id)
            logging.info(f"{self.id} Started {process_id}")

        async def on_stop(exit_code):
            # process_id may be reused with other runners so clean up handler
            self.process_handlers.pop(process_id, None)
            await self.send("stopped", {"exitCode": exit_code}, process_id)
            logging.info(f"{self.id} Stopped {process_id}")

        async def on_output(channel, output):
            await self.send(channel, {"output": output}, process_id)
            logging.debug(f"{self.id} Sending Output {process_id} {channel} {output}")

        async def on_display_activity(connection_details: VncConnectionDetails):
            logging.debug(f"{self.id} Sending display activity")
            await self.send(
                "novnc",
                {
                    "port": connection_details.port,
                    "path": connection_details.path,
                },
                process_id,
            )

        handler = handler_class(self.user, self.pty)
        handler.on_start = on_start
        handler.on_stop = on_stop
        handler.on_display_activity = on_display_activity
        handler.on_output = on_output
        await handler.start(path, code, novncOptions=novncOptions)

        self.process_handlers[process_id] = handler


bt_run_manager = None


async def bluetooth_run_handler(device, uuid, message, characteristic_to_report_on):
    try:
        message_dict = bytearray_to_dict(message)
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise Exception("Error: invalid format")

    try:
        user = message_dict.get("user", None)
        pty = message_dict.get("pty", "").lower() in ["1", "true"]
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise

    # TODO: handle multiple 'run' connections
    global bt_run_manager
    if bt_run_manager is None:

        def send_func(message):
            device.write_value(message, characteristic_to_report_on)

        bt_run_manager = RunManager(send_func, user=user, pty=pty)
        logging.debug(f"{bt_run_manager.id} New connection")

    logging.debug(f"{bt_run_manager.id} Received Message {message_dict}")
    try:
        await bt_run_manager.handle_message(message)
    except Exception as e:
        logging.exception(f"{bt_run_manager.id} Message Exception: {e}")
        await bt_run_manager.stop()
        bt_run_manager = None
        raise


async def run(request):
    query_params = request.query
    user = query_params.get("user", None)
    pty = query_params.get("pty", "").lower() in ["1", "true"]

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    async def send_func(message):
        try:
            await socket.send_str(message)
        except ConnectionResetError:
            pass  # already disconnected

    run_manager = RunManager(send_func, user=user, pty=pty)
    logging.info(f"{run_manager.id} New connection")

    try:
        async for message in socket:
            logging.debug(f"{run_manager.id} Received Message {message.data}")
            await run_manager.handle_message(message.data)

    except asyncio.CancelledError:
        pass

    finally:
        await socket.close()
        logging.info(f"{run_manager.id} Closed connection")
        await run_manager.stop()

    return socket
