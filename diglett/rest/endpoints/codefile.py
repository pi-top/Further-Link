# coding=utf-8
import logging

from flask import request
from flask_restplus import Namespace, Resource

from diglett.base.beanret import BeanRet
from diglett.base.file_tool import FileTool
from diglett.rest.endpoints.serializers import bean

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

log = logging.getLogger(__name__)
ns_file = Namespace(name='file', description='Describes the operations related with the teams')
parser = ns_file.parser()
parser.add_argument('path', type=str, required=True, help='The path like  /xx/xx/xx.py', location='form')
parser.add_argument('content', type=str, help='The file content', location='form')

parser_reaname = ns_file.parser()
parser_reaname.add_argument('oldPath', type=str, required=True, help='old path', location='form')
parser_reaname.add_argument('newPath', type=str, required=True, help='new path', location='form')


@ns_file.route("/")
@ns_file.param('path', 'The path like  /xx/xx/xx.py')
class CodeFile(Resource):
    @ns_file.doc(parser=parser)
    @ns_file.marshal_with(bean)
    def post(self):
        """
        create & write the content to the file
        :return:
        """
        path = request.form.get("path")
        content = request.form.get("content")
        if not path and not content:
            return BeanRet(success=False)

        file_tool = FileTool()
        file_path = file_tool.workspace(path)
        if path and content:
            file_tool.write(file_path, content)
        elif path and not content:
            file_tool.create_folder(file_path)
        else:
            return BeanRet(success=False)

        return BeanRet(success=True)

    @ns_file.doc(parser=parser_reaname)
    @ns_file.marshal_with(bean)
    def put(self):
        """
        rename the old path to the new path,if it is a file just rename the file name,
        but if it is a folder and has some sub folders, it will iterate all of them and
        move them to the folder
        :return:
        """
        old_path = request.form.get("oldPath")
        new_path = request.form.get("newPath")
        if not old_path or not new_path:
            return BeanRet(success=False)
        file_tool = FileTool()
        root_path = file_tool.workspace()
        file_tool.rename(root_path, old_path, new_path)
        return BeanRet(success=True)

    @ns_file.marshal_with(bean)
    def get(self):
        """
        read python file content
        :return:  content
        """
        path = request.args.get("path")
        if not path:
            return BeanRet(success=False)

        file_tool = FileTool()
        file_path = file_tool.workspace(path)
        content = file_tool.read(file_path)

        if content:
            return BeanRet(success=True, data={"content": content})
        else:
            return BeanRet(success=False)

    @ns_file.doc(parser=parser)
    @ns_file.marshal_with(bean)
    def delete(self):
        """
        remove file
        :return: True
        """
        path = request.form.get("path")
        if not path:
            return BeanRet(success=False)

        file_tool = FileTool()
        file_path = file_tool.workspace(path)
        all_file = file_tool.all_file(file_path, is_dir=False, filter=file_tool.workspace())
        file_tool.remove(file_path)
        return BeanRet(success=True, data=all_file)
