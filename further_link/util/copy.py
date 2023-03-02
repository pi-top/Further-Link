from shutil import copytree, rmtree

from .user_config import get_miniscreen_projects_directory


async def do_copy_files_to_projects_directory(src_directory, directory, user=None):
    dst_directory = get_miniscreen_projects_directory(
        directory.get("name"), user, directory.get("username")
    )
    rmtree(dst_directory, ignore_errors=True)
    copytree(src_directory, dst_directory, symlinks=False)
