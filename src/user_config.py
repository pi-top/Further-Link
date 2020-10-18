import pwd
import getpass


def get_current_user():
    return getpass.getuser()


def user_exists(user):
    for existing_user in pwd.getpwall():
        if existing_user.pw_name == user:
            return True
    return False


def get_working_directory(user):
    for existing_user in pwd.getpwall():
        if existing_user.pw_name == user:
            return existing_user.pw_dir
    return None
