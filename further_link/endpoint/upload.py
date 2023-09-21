import json
import logging

from aiohttp import web

from ..util.bluetooth.utils import bytearray_to_dict
from ..util.copy import do_copy_files_to_projects_directory
from ..util.upload import BadUpload, directory_is_valid, do_upload, get_directory_path
from ..util.user_config import get_working_directory


def is_miniscreen_project(files):
    for filename in files:
        if filename == "project.cfg":
            return True
    return False


async def handle_upload(directory, work_dir, user):
    fetched_urls = await do_upload(directory, work_dir, user)

    if is_miniscreen_project(directory.get("files", {})):
        await do_copy_files_to_projects_directory(
            get_directory_path(work_dir, directory.get("name")),
            directory,
            user,
        )

    return fetched_urls


async def upload(request):
    query_params = request.query
    user = query_params.get("user", None)

    work_dir = get_working_directory(user)

    try:
        directory = await request.json()
        if not directory_is_valid(directory):
            raise web.HTTPBadRequest(reason=f"Invalid upload directory: {directory}")

        fetched_urls = await handle_upload(directory, work_dir, user)

    except (web.HTTPBadRequest, json.decoder.JSONDecodeError) as e:
        logging.exception(e)
        raise web.HTTPBadRequest()

    except BadUpload as e:
        logging.exception(e)
        raise web.HTTPInternalServerError()

    return web.Response(
        text=json.dumps({"success": True, "fetched_urls": fetched_urls})
    )


async def bt_upload(interface, uuid, message: bytearray):
    try:
        message_dict = bytearray_to_dict(message)
    except json.decoder.JSONDecodeError as e:
        logging.exception(f"Error: {e}")
        interface.write_value(b"Error: invalid format", uuid)
        return

    try:
        user = message_dict.get("user", None)
        work_dir = get_working_directory(user)

        if not directory_is_valid(message_dict):
            msg = f"Invalid upload directory: {message_dict}"
            interface.write_value(msg, uuid)
            return
        fetched_urls = await handle_upload(message_dict, work_dir, user)
    except Exception as e:
        logging.exception(f"{e}")
        interface.write_value(f"Error: {e}", uuid)

    interface.write_value(
        json.dumps({"success": True, "fetched_urls": fetched_urls}), uuid
    )
