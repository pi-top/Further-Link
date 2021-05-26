import os

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
WORKING_DIRECTORY = "{}/work_dir".format(TEST_PATH)

BASE_URL = 'ws://0.0.0.0:8028'
STATUS_URL = BASE_URL + '/status'
VERSION_URL = BASE_URL + '/version'
RUN_URL = BASE_URL + '/run'
RUN_PY_URL = BASE_URL + '/run-py'
