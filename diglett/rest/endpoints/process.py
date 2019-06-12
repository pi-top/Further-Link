# coding=utf-8
import logging
import os

from flask import Blueprint, request, json
from flask_restplus import Namespace, Resource

from diglett import logger
from diglett.base.beanret import BeanRet
from diglett.base.file_tool import FileTool
from diglett.entity.tree_vo import TreeVO
from diglett.rest.endpoints.process_thread import Process
from diglett.rest.endpoints.serializers import code_vo, bean

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

pitop = Blueprint('process', __name__, url_prefix="/process")
ws = Blueprint('ws_process', __name__)

log = logging.getLogger(__name__)
ns_process = Namespace(name='process', description='Describes the operations related with the teams')
parser = ns_process.parser()
parser.add_argument('path', type=str, required=True, help='The path like  /xx/xx/xx.py', location='form')
parser.add_argument('content', type=str, help='The file content≈', location='form')


@ws.route('/process/ws')
def process(socket):
    global process_ws
    process_ws = socket
    while not socket.closed:
        message = socket.receive()
        if not message:
            logger.info(str(message))


@ns_process.route("/")
class InitProject(Resource):
    @ns_process.expect([code_vo])
    @ns_process.marshal_with(bean)
    def post(self):
        """
        init project files
        :return: BeanRet
        """
        codes = request.json
        file_tool = FileTool()
        workspace = file_tool.workspace()
        scan_workspace = None
        for code in codes:
            if not scan_workspace:
                scan_workspace = workspace + code["projectVersionId"]

            file_path = workspace + code["projectVersionId"] + "/" + code["path"]
            file_tool.create_file(file_path)
            file_tool.write(file_path, code["content"])

        tree_vo = TreeVO()
        tree_vo.file_path = scan_workspace
        tree_vo_result = self.__list_file(tree_vo.__dict__, workspace, codes)
        return BeanRet(success=True, data=tree_vo_result["children"])

    def __list_file(self, tree_vo, workspace, codes):
        """
        scan files and build a tree data for frontend file tree
        :param tree_vo:
        :param workspace:
        :param codes:
        :return: []
        """
        file_path = tree_vo["file_path"]
        file_list = os.listdir(file_path)
        list = []

        for file in file_list:
            tree_vo_tmp = TreeVO()
            tree_vo_tmp.file_path = file_path + "/" + file
            tree_vo_tmp.path = tree_vo_tmp.file_path.replace(workspace, "")
            tree_vo_tmp.key = tree_vo_tmp.path
            tree_vo_tmp.title = file
            tree_vo_tmp.is_leaf = False
            if os.path.isfile(tree_vo_tmp.file_path):
                for code in codes:
                    if (code["projectVersionId"] + "/" + code["path"]).__eq__(
                            tree_vo_tmp.file_path.replace(workspace, "")):
                        tree_vo_tmp.id = code["id"]

                tree_vo_tmp.is_leaf = True
                list.append(tree_vo_tmp.__dict__)
            elif os.path.isdir(tree_vo_tmp.file_path):
                list.append(self.__list_file(tree_vo_tmp.__dict__, workspace, codes))

        tree_vo["children"] = list
        return tree_vo

    @ns_process.doc(parser=parser)
    @ns_process.marshal_with(bean)
    def get(self):
        """
        exec a python file
        1.check the file exist
        2.exec the file
        :return: BeanRet
        """
        path = request.args.get("path")
        file_tool = FileTool()
        pyfile = file_tool.workspace(path)
        # 1.check the file exist
        if os.path.exists(pyfile):
            # 2.exec the file
            cmd = file_tool.python3_cmd(pyfile)
            global process_thread
            process_thread = Process(cmd, process_ws)
            process_thread.start()

        return BeanRet(success=True)

    @ns_process.marshal_with(bean)
    def put(self):
        """
        stop exec thread
        :return:
        """
        if process_thread and process_thread.is_alive():
            process_thread.stop()
        return BeanRet(success=True)
