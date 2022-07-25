import asyncio
import logging

from aiohttp import web
from pt_web_vnc.connection_details import VncConnectionDetails

from ..runner.exec_process_handler import ExecProcessHandler
from ..runner.process_handler import InvalidOperation
from ..runner.py_process_handler import PyProcessHandler
from ..runner.shell_process_handler import ShellProcessHandler
from ..util.message import BadMessage, create_message, parse_message
from ..util.user_config import default_user, get_temp_dir


class RunManager:
    def __init__(self, socket, user=None, pty=False):
        self.socket = socket
        self.user = default_user() if user is None else user
        self.pty = pty

        self.id = str(id(self))
        self.process_handlers = {}
        self.handler_classes = {
            "exec": ExecProcessHandler,
            "python3": PyProcessHandler,
            "shell": ShellProcessHandler,
        }

    async def stop(self):
        for p in self.process_handlers.values():
            try:
                await p.stop()
            except InvalidOperation:
                pass

    async def send(self, type, data=None, process_id=None):
        try:
            await self.socket.send_str(create_message(type, data, process_id))
        except ConnectionResetError:
            pass  # already disconnected

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
                novnc = m_data.get("novnc")
                novnc = novnc if isinstance(novnc, bool) else False
                await self.add_handler(m_process, m_data["runner"], path, code, novnc)

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

    async def add_handler(self, process_id, runner, path, code, novnc):
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
        await handler.start(path, code, novnc=novnc)

        self.process_handlers[process_id] = handler


async def run(request):
    query_params = request.query
    user = query_params.get("user", None)
    pty = query_params.get("pty", "").lower() in ["1", "true"]

    socket = web.WebSocketResponse()
    await socket.prepare(request)

    run_manager = RunManager(socket, user=user, pty=pty)
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
