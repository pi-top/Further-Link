import asyncio
import logging
from typing import Callable, Dict, Optional

from aiohttp import web
from pt_web_vnc.connection_details import VncConnectionDetails

from ..runner.exec_process_handler import ExecProcessHandler
from ..runner.process_handler import InvalidOperation
from ..runner.py_process_handler import PyProcessHandler
from ..runner.shell_process_handler import ShellProcessHandler
from ..util.bluetooth.utils import bytearray_to_dict
from ..util.connection_types import ConnectionType
from ..util.message import BadMessage, create_message, parse_message
from ..util.user_config import default_user, get_temp_dir


class Timer:
    """
    Class that calls a callback after a specified timeout.
    Similar to threading.Timer but supports asyncio
    """

    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = None

    def start(self):
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        if self._callback and callable(self._callback):
            await self._callback()

    def cancel(self):
        if self._task:
            self._task.cancel()
            self._task = None


class RunManager:
    WATCHDOG_TIMEOUT = 10

    def __init__(
        self,
        send_func: Callable,
        client_uuid: str,
        user=None,
        pty=False,
        connection_type: ConnectionType = ConnectionType.WEBSOCKET,
    ):
        self.send_func = send_func
        self.client_uuid = client_uuid
        self.user = default_user() if user is None else user
        self.pty = pty
        self.connection_type = connection_type

        self.id = str(id(self))
        self.process_handlers: Dict = {}
        self.handler_classes = {
            "exec": ExecProcessHandler,
            "python3": PyProcessHandler,
            "shell": ShellProcessHandler,
        }
        self.message_callbacks: Dict = {}

        self._watchdog_callback: Optional[Callable] = None
        self._watchdog_timer: Optional[Timer] = None

    def start_watchdog_timer(self, callback: Callable):
        self._watchdog_callback = callback
        self.restart_watchdog_timer()

    def stop_watchdog_timer(self):
        if isinstance(self._watchdog_timer, Timer):
            self._watchdog_timer.cancel()

    def restart_watchdog_timer(self):
        self.stop_watchdog_timer()
        self._watchdog_timer = Timer(self.WATCHDOG_TIMEOUT, self._watchdog_callback)
        self._watchdog_timer.start()

    async def stop(self):
        # the dictionary will be mutated so use list to make a copy
        for p in list(self.process_handlers.values()):
            try:
                await p.stop()
            except InvalidOperation:
                pass

        self.stop_watchdog_timer()

    async def send(self, type, data=None, process_id=None):
        client_uuid = self.client_uuid
        await self.send_func(create_message(type, client_uuid, data, process_id))

    def set_message_callback(self, message_type, callback):
        self.message_callbacks[message_type] = callback

    async def handle_message(self, message):
        try:
            m_type, m_data, m_process, _ = parse_message(message)

            process_handler = self.process_handlers.get(m_process)

            if m_type == "ping":
                if self._watchdog_timer:
                    self.restart_watchdog_timer()
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

        handler = handler_class(self.user, self.pty, self.connection_type)
        handler.on_start = on_start
        handler.on_stop = on_stop
        handler.on_display_activity = on_display_activity
        handler.on_output = on_output
        await handler.start(path, code, novncOptions=novncOptions)

        self.process_handlers[process_id] = handler


async def bluetooth_run_handler(
    device,
    message,
    characteristic_to_report_on,
    bt_run_managers,
):
    try:
        message_dict = bytearray_to_dict(message)
    except Exception:
        msg = "Error: invalid format"
        logging.error(msg)
        return

    client_uuid = message_dict.pop("client", None)
    if client_uuid is None:
        msg = "Error: client_uuid not provided in message"
        logging.error(msg)
        return

    if bt_run_managers.get(client_uuid) is None:

        async def send_func(message):
            logging.debug(f"Sending: {message[0:120]}")
            await device.write_value(message, characteristic_to_report_on)

        # after a few seconds of inactivity, stop and remove RunManager
        async def on_timeout_callback():
            logging.warning(
                f"RunManager for client {client_uuid} timed out, cleaning up..."
            )
            try:
                run_manager = bt_run_managers.get(client_uuid)
                if run_manager:
                    await run_manager.stop()
                    del bt_run_managers[client_uuid]
            except Exception as e:
                logging.error(f"Error while cleaning up run manager: {e}")

        run_manager = RunManager(
            send_func,
            client_uuid=client_uuid,
            user=None,
            pty=True,
            connection_type=ConnectionType.BLUETOOTH,
        )
        run_manager.start_watchdog_timer(on_timeout_callback)
        logging.info(f"{run_manager.id} New connection")
        bt_run_managers[client_uuid] = run_manager

    run_manager = bt_run_managers.get(client_uuid)
    logging.debug(f"{run_manager.id} Received Message {message_dict}")

    try:
        await run_manager.handle_message(message)
    except Exception as e:
        msg = f"{run_manager.id} Message Exception: {e}"
        logging.error(msg)
        await device.write_value(msg, characteristic_to_report_on)
        await run_manager.stop()
        del bt_run_managers[client_uuid]


async def run(request):
    query_params = request.query
    client_uuid = query_params.get("client", "")
    user = query_params.get("user", None)
    pty = query_params.get("pty", "").lower() in ["1", "true"]

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    async def send_func(message):
        try:
            await socket.send_str(message)
        except ConnectionResetError:
            pass  # already disconnected

    run_manager = RunManager(
        send_func,
        client_uuid=client_uuid,
        user=user,
        pty=pty,
        connection_type=ConnectionType.WEBSOCKET,
    )
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
