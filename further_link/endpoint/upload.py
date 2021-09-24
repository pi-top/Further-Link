import json

from aiohttp import web

from ..util.upload import BadUpload, directory_is_valid, do_upload
from ..util.user_config import get_working_directory


async def upload(request):
    query_params = request.query
    user = query_params.get("user", None)

    work_dir = get_working_directory(user)

    try:
        directory = await request.json()

        if not directory_is_valid(directory):
            raise web.HTTPBadRequest()

        await do_upload(directory, work_dir)

    except (web.HTTPBadRequest, json.decoder.JSONDecodeError):
        raise web.HTTPBadRequest()

    except BadUpload:
        raise web.HTTPInternalServerError()

    return web.Response(text="OK")
