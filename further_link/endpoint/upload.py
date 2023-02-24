import json
from os import path

from aiohttp import web

from ..util.upload import BadUpload, directory_is_valid, do_upload
from ..util.user_config import default_user, get_working_directory


def is_miniscreen_project(directory):
    for filename in directory.get("files", {}):
        if filename.endswith(".cfg"):
            return True
    return False


async def upload(request):
    query_params = request.query
    user = query_params.get("user", None)

    work_dir = get_working_directory(user)

    try:
        directory = await request.json()

        if not directory_is_valid(directory):
            raise web.HTTPBadRequest()

        # Upload to further directory
        await do_upload(directory, work_dir, user)

        # Upload to projects directory to run using miniscreen app
        if is_miniscreen_project(directory):
            if user is None:
                user = default_user()
            user_home = path.expanduser(f"~{user}")
            project_work_dir = f"{user_home}/Desktop/Projects"
            await do_upload(directory, project_work_dir, user, use_cache=False)

    except (web.HTTPBadRequest, json.decoder.JSONDecodeError):
        raise web.HTTPBadRequest()

    except BadUpload:
        raise web.HTTPInternalServerError()

    return web.Response(text="OK")
