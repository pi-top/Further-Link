# coding=utf-8
import logging
import os

from flask import Blueprint, request, json
from flask_restplus import Namespace, Resource

from diglett.base.beanret import BeanRet
from diglett.base.command import Command
from diglett.base.file_tool import FileTool
from diglett.rest.endpoints.process_thread import Process
from diglett.rest.endpoints.serializers import bean, code_vo

"""
this is main process of python file exec on OS,
it will create file and change file content,it can running it
stop it.

1.create python file and stop running
2.run python file and return result
"""

ws = Blueprint('ws_exec', __name__)

log = logging.getLogger(__name__)
ns_exec = Namespace(name='exec', description='Describes the operations related with the teams')


@ws.route('/ws/exec')
def exec_websocket(socket):
    global process_ws
    process_ws = socket
    while not socket.closed:
        message = socket.receive()
        if message:
            log.info(str(message))
            data = json.loads(message)
            projectVersionId = data["projectVersionId"]

            if data["cmd"].__eq__(Command.Start.value):
                path = projectVersionId + "/" + data["data"]["path"]
                content = data["data"]["content"]

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

            elif data["cmd"].__eq__(Command.Stop.value):
                if process_thread and process_thread.is_alive():
                    process_thread.stop()
                    file_tool = FileTool()
                    file_path = file_tool.workspace(projectVersionId)
                    file_tool.remove(file_path)
            elif data["cmd"].__eq__(Command.Input.value):
                pass
            else:
                pass


@ns_exec.route("/")
class Project(Resource):
    @ns_exec.expect([code_vo])
    @ns_exec.marshal_with(bean)
    def post(self):
        """
        init project files
        :return: BeanRet
        """
        codes = request.json
        file_tool = FileTool()
        workspace = file_tool.workspace()
        for code in codes:
            file_path = workspace + code["projectVersionId"] + "/" + code["path"]
            file_tool.create_file(file_path)
            file_tool.write(file_path, code["content"])

        return BeanRet(success=True)
