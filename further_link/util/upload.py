import os
from shutil import rmtree

import aiofiles
from aiohttp import ClientSession

from ..util.user_config import default_user, get_gid, get_uid
from .user_config import CACHE_DIR_NAME

file_types = ["url", "text"]


class BadUpload(Exception):
    pass


def file_is_valid(file):
    return (
        "type" in file
        and file["type"] in file_types
        and "content" in file
        and isinstance(file["content"], dict)
    )


def directory_is_valid(directory):
    return (
        "name" in directory
        and isinstance(directory["name"], str)
        and "files" in directory
        and isinstance(directory["files"], object)
        and all(file_is_valid(file) for file in directory["files"].values())
    )


def create_directory(directory_path: str, user: str = None):
    """
    Create the directories from the provided path level by level, making sure the folders have the correct owner
    """
    if user is None:
        user = default_user()

    splitted_path = directory_path.split("/")
    subpaths = ["/".join(splitted_path[:i]) for i in range(2, len(splitted_path) + 1)]

    for subpath in subpaths:
        if not os.path.isdir(subpath):
            os.mkdir(subpath)

            # Update directory owner if on user home
            if user and subpath.startswith(os.path.expanduser(f"~{user}")):
                os.chown(subpath, uid=get_uid(user), gid=get_gid(user))


def valid_url_content(content):
    return (
        "url" in content
        and isinstance(content["url"], str)
        and "bucketName" in content
        and isinstance(content["bucketName"], str)
        and "fileName" in content
        and isinstance(content["fileName"], str)
    )


def valid_text_content(content):
    return "text" in content and isinstance(content["text"], str)


async def download_file(url, file_path, user=None):
    async with ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200

            async with aiofiles.open(file_path, "wb") as file:
                await file.write(await response.read())

    # set ownership of file to user
    if user:
        os.chown(file_path, uid=get_uid(user), gid=get_gid(user))


def get_directory_path(work_dir, directory_name):
    directory_path = os.path.join(work_dir, directory_name)

    # directory_path should be subdir of work_dir
    if not is_sub_directory(directory_path, work_dir):
        raise Exception(f"Forbidden directory name {directory_name}")

    return directory_path


def get_alias_path(directory_path, alias_name):
    alias_path = os.path.join(directory_path, alias_name)

    # alias_path should be subdir of directory_path
    if not is_sub_directory(alias_path, directory_path):
        raise Exception(f"Forbidden alias name {alias_name}")

    return alias_path


def get_bucket_cache_path(work_dir, bucket_name):
    cache_path = os.path.join(work_dir, CACHE_DIR_NAME)
    bucket_cache_path = os.path.join(cache_path, bucket_name)

    # bucket_cache_path should be subdir of cache_path
    if not is_sub_directory(bucket_cache_path, cache_path):
        raise Exception(f"Forbidden bucket name {bucket_name}")

    return bucket_cache_path


def get_cache_file_path(bucket_cache_path, file_name):
    cache_file_path = os.path.join(bucket_cache_path, file_name)

    # cache_file_path should be subdir of bucket_cache_path
    if not is_sub_directory(cache_file_path, bucket_cache_path):
        raise Exception(f"Forbidden file name {file_name}")

    return cache_file_path


def is_sub_directory(sub_dir, from_dir):
    return os.path.realpath(sub_dir).startswith(os.path.realpath(from_dir))


async def do_upload(directory, work_dir, user=None, use_cache=True):
    try:
        if user is None:
            user = default_user()

        directory_name = directory["name"]
        directory_path = get_directory_path(work_dir, directory_name)

        create_directory(directory_path, user)

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

        for alias_name, file_info in directory["files"].items():
            alias_path = get_alias_path(directory_path, alias_name)

            # support for creating subdirs in alias name
            alias_dir = os.path.dirname(alias_path)
            if not os.path.exists(alias_dir):
                create_directory(alias_dir, user)

            if file_info["type"] == "url":
                content = file_info["content"]

                if not valid_url_content(content):
                    raise Exception("Invalid url content")

                bucket_name = content["bucketName"]
                file_name = content["fileName"]
                url = content["url"]

                if not use_cache:
                    await download_file(url, f"{alias_dir}/{file_name}", user)
                    continue

                # url type files have a cache dir to prevent repeat download
                bucket_cache_path = get_bucket_cache_path(work_dir, bucket_name)
                if not os.path.exists(bucket_cache_path):
                    create_directory(bucket_cache_path, user)

                cache_file_path = get_cache_file_path(bucket_cache_path, file_name)
                # only download the file if it's not in the cache
                if not os.path.exists(cache_file_path):
                    await download_file(url, cache_file_path, user)

                # create a symlink pointing to the cached downloaded file
                os.symlink(cache_file_path, alias_path)

            elif file_info["type"] == "text":
                content = file_info["content"]

                if not valid_text_content(content):
                    raise Exception("Invalid text content")

                async with aiofiles.open(alias_path, "w+") as file:
                    await file.write(content["text"])

                # set ownership of file to the correct user
                if user:
                    os.chown(alias_path, uid=get_uid(user), gid=get_gid(user))

    except Exception as e:
        raise BadUpload(e)
