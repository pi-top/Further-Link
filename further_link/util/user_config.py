import getpass
import grp
import os
import pwd

from .sdk import get_user_using_first_display

DEFAULT_USER = "pi"
DEFAULT_DIR_NAME = "further"
DEFAULT_PROJECTS_DIR = "Desktop/Projects/Further"
CACHE_DIR_NAME = ".flcache"
TEMP_DIR = "/tmp"
FURTHER_LINK_WORK_DIR = "FURTHER_LINK_WORK_DIR"
FURTHER_LINK_TEMP_DIR = "FURTHER_LINK_TEMP_DIR"
FURTHER_LINK_MINISCREEN_PROJECTS_DIR = "FURTHER_LINK_MINISCREEN_PROJECTS_DIR"


def get_current_user():
    return getpass.getuser()


def user_exists(user):
    try:
        return pwd.getpwnam(user) is not None
    except (KeyError, TypeError):
        return False


def get_uid(user):
    try:
        return pwd.getpwnam(user).pw_uid
    except (KeyError, TypeError):
        return None


def get_gid(user):
    try:
        return pwd.getpwnam(user).pw_gid
    except (KeyError, TypeError):
        return None


def get_home_directory(user):
    try:
        return pwd.getpwnam(user).pw_dir
    except (KeyError, TypeError):
        return None


def get_shell(user):
    try:
        return pwd.getpwnam(user).pw_shell
    except (KeyError, TypeError):
        return None


def get_grp_ids(user):
    try:
        groups = [g.gr_gid for g in grp.getgrall() if user in g.gr_mem]
        gid = pwd.getpwnam(user).pw_gid
        groups.append(gid)
        return groups
    except (KeyError, TypeError):
        return None


def default_user():
    user = get_user_using_first_display()
    if user:
        return user

    user = get_current_user()
    if user:
        return user

    return DEFAULT_USER


def get_temp_dir():
    return os.environ.get(FURTHER_LINK_TEMP_DIR, TEMP_DIR)


def get_working_directory(user=None):
    from_env = os.environ.get(FURTHER_LINK_WORK_DIR)
    if from_env is not None:
        return from_env

    if user is None or not user_exists(user):
        user = default_user()

    return os.path.join(get_home_directory(user), DEFAULT_DIR_NAME)


def get_miniscreen_projects_directory(name, user, username):
    if user is None or not user_exists(user):
        user = default_user()
    if username is None:
        username = "unknown"

    base_dir = os.path.join(get_home_directory(user), DEFAULT_PROJECTS_DIR)

    from_env = os.environ.get(FURTHER_LINK_MINISCREEN_PROJECTS_DIR)
    if from_env is not None:
        base_dir = from_env

    # Username might be an email address, so we only want the first part
    return os.path.join(base_dir, username.split("@")[0], name)


def get_xdg_runtime_dir(user=None):
    uid = get_uid(user)
    xdg_runtime_dir = f"/run/user/{uid}"

    if os.path.exists(xdg_runtime_dir):
        return xdg_runtime_dir

    return None


def get_absolute_path(path, root="/"):
    # path is absolute or relative to root
    is_absolute = path[0] == "/"
    if not is_absolute:
        return os.path.join(root, path)
    return path
