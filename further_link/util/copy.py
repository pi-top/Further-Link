import logging
import os
from shutil import copytree, rmtree

from .user_config import (
    default_user,
    get_gid,
    get_miniscreen_projects_directory,
    get_uid,
)


def set_directory_ownership(directory, user, recurse=True):
    os.chown(directory, uid=get_uid(user), gid=get_gid(user))
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if recurse and os.path.isdir(file_path):
                set_directory_ownership(file_path, user)
            else:
                os.chown(file_path, uid=get_uid(user), gid=get_gid(user))
        except Exception as e:
            logging.error(f"Error setting '{file_path}' ownership to '{user}': {e}")


async def do_copy_files_to_projects_directory(src_directory, directory, user=None):
    if user is None:
        user = default_user()

    dst_directory = get_miniscreen_projects_directory(
        directory.get("name"), user, directory.get("username")
    )
    rmtree(dst_directory, ignore_errors=True)
    copytree(src_directory, dst_directory, symlinks=False)
    set_directory_ownership(dst_directory, user)
