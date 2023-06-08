import json
import logging

from aiohttp import web

from ..util.copy import do_copy_files_to_projects_directory
from ..util.upload import BadUpload, directory_is_valid, do_upload, get_directory_path
from ..util.user_config import get_working_directory


def is_miniscreen_project(files):
    for filename in files:
        if filename == "project.cfg":
            return True
    return False


async def upload(request):
    query_params = request.query
    user = query_params.get("user", None)

    work_dir = get_working_directory(user)

    try:
        directory = await request.json()

        if not directory_is_valid(directory):
            raise web.HTTPBadRequest(reason=f"Invalid upload directory: {directory}")

        await do_upload(directory, work_dir, user)

        if is_miniscreen_project(directory.get("files", {})):
            await do_copy_files_to_projects_directory(
                get_directory_path(work_dir, directory.get("name")),
                directory,
                user,
            )

    except (web.HTTPBadRequest, json.decoder.JSONDecodeError) as e:
        logging.exception(e)
        raise web.HTTPBadRequest()

    except BadUpload as e:
        logging.exception(e)
        raise web.HTTPInternalServerError()

    return web.Response(text="OK")
