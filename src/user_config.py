import os
import pwd
import getpass


DEFAULT_USER = 'pi'
DEFAULT_DIR_NAME = 'further'
CACHE_DIR_NAME = '.flcache'
TEMP_DIR = '/tmp'
FURTHER_LINK_WORK_DIR = 'FURTHER_LINK_WORK_DIR'
FURTHER_LINK_TEMP_DIR = 'FURTHER_LINK_TEMP_DIR'


def get_current_user():
    return getpass.getuser()


def user_exists(user):
    for existing_user in pwd.getpwall():
        if existing_user.pw_name == user:
            return True
    return False


def get_home_directory(user):
    for existing_user in pwd.getpwall():
        if existing_user.pw_name == user:
            return existing_user.pw_dir
    return None


def default_user():
    return DEFAULT_USER if user_exists(DEFAULT_USER) else get_current_user()


def get_temp_dir():
    return os.environ.get(FURTHER_LINK_TEMP_DIR, TEMP_DIR)


def get_working_directory(user=None):
    from_env = os.environ.get(FURTHER_LINK_WORK_DIR)
    if from_env is not None:
        return from_env

    if user is None or not user_exists(user):
        user = default_user()

    return os.path.join(get_home_directory(user), DEFAULT_DIR_NAME)
