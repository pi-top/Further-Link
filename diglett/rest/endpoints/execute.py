# coding=utf-8
import logging
import os

from flask import Blueprint, request
from flask_restplus import Namespace, Resource

from diglett import logger
from diglett.base.beanret import BeanRet
from diglett.base.file_tool import FileTool
from diglett.rest.endpoints.process_thread import Process
from diglett.rest.endpoints.serializers import bean, exec_code

"""
this is main process of python file exec on OS,
it will create file and change file content,it can running it
stop it.

1.create python file and stop running
2.run python file and return result
3.init project from further
4.rename a file and folder
5.write code to file
6.read file content to webide frontend
7.delete file and folder ,if there some files and sub folders delete all of them
"""

ws = Blueprint('ws_exec', __name__)

log = logging.getLogger(__name__)
ns_exec = Namespace(name='exec', description='Describes the operations related with the teams')


@ws.route('/exec/ws')
def exec_websocket(socket):
    global process_ws
    process_ws = socket
    while not socket.closed:
        message = socket.receive()
        if not message:
            logger.info(str(message))


@ns_exec.route("/")
class Project(Resource):
    @ns_exec.expect(exec_code)
    @ns_exec.marshal_with(bean)
    def post(self):
        """
        exec a python file
        1.check the file exist
        2.exec the file
        :return: BeanRet
        """
        exec_code = request.json
        path = exec_code["path"]
        content = exec_code["content"]
        if not path and not content:
            return BeanRet(success=False)

        # 1.check the file exist
        file_tool = FileTool()
        file_path = file_tool.workspace(path)
        if not os.path.exists(file_path):
            file_tool.write(file_path, content)

        # 2.exec the file
        cmd = file_tool.python3_cmd(file_path)
        global process_thread
        process_thread = Process(cmd, process_ws)
        process_thread.start()

        return BeanRet(success=True)

    @ns_exec.marshal_with(bean)
    def put(self):
        """
        stop exec thread
        :return:
        """
        if process_thread and process_thread.is_alive():
            process_thread.stop()
        return BeanRet(success=True)
