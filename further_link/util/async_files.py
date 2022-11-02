import asyncio
import os
from functools import partial
from shutil import rmtree

from aiohttp import ClientSession

from .user_config import default_user, get_gid, get_uid

# async file helpers. used instead of aiofiles mainly avoid
# packaging the new more complete versions for debian. aiofiles can still be used if preferred

# some sync methods are acceptable, such as os.path methods that only do string
# manipulation or os.remove which blocks no more than starting a thread would


async def exists(path):
    return await asyncio.to_thread(partial(os.path.exists, path))


async def chmod(fd, mode):
    await asyncio.to_thread(partial(os.chmod, fd, mode))


async def chown(fd, uid, gid):
    await asyncio.to_thread(partial(os.chown, fd, uid, gid))


async def symlink(src, dst):
    await asyncio.to_thread(partial(os.symlink, src, dst))


async def write_file(path, content, mode="w+"):
    def sync_write_file(p, c):
        print("opening file")
        with open(p, mode) as file:
            print("file open")
            file.write(c)
        print("file written")

    await asyncio.to_thread(partial(sync_write_file, path, content))


async def download_file(url, file_path):
    async with ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200

            await write_file(file_path, await response.read(), "wb")


async def create_directory(directory_path: str, user: str = None):
    def _create_directory(directory_path: str, user: str = None):
        """
        Create the directories from the provided path level by level, making sure the folders have the correct owner
        """
        if user is None:
            user = default_user()

        splitted_path = directory_path.split("/")
        subpaths = [
            "/".join(splitted_path[:i]) for i in range(2, len(splitted_path) + 1)
        ]

        for subpath in subpaths:
            if not os.path.isdir(subpath):
                os.mkdir(subpath)

                # Update directory owner if on user home
                if user and subpath.startswith(os.path.expanduser(f"~{user}")):
                    os.chown(subpath, uid=get_uid(user), gid=get_gid(user))

    await asyncio.to_thread(partial(_create_directory, directory_path, user))


async def clear_directory(directory_path: str):
    def _clear_directory(directory_path: str):
        # clear the upload directory every time
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    rmtree(file_path)
            except Exception:
                pass

    await asyncio.to_thread(partial(_clear_directory, directory_path))


async def create_empty_directory(directory_path: str, user: str = None):
    await create_directory(directory_path, user)
    # in case the directory already existed, ensure it is empty
    await clear_directory(directory_path)
