import os

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
WORKING_DIRECTORY = "{}/work_dir".format(TEST_PATH)

BASE_URL = '0.0.0.0:8028'
WS_BASE_URL = 'ws://' + BASE_URL
HTTP_BASE_URL = 'http://' + BASE_URL
STATUS_URL = HTTP_BASE_URL + '/status'
VERSION_URL = HTTP_BASE_URL + '/version'
UPLOAD_URL = HTTP_BASE_URL + '/upload'
RUN_URL = WS_BASE_URL + '/run'
RUN_PY_URL = WS_BASE_URL + '/run-py'
