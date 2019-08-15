import configparser
import os
import shutil

from settings import PITOP_CONF


class Singleton(object):
    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls)
        return cls._instance


class FileTool(Singleton):
    def __init__(self):
        self.cf = configparser.ConfigParser()
        self.cf.read(PITOP_CONF)

    def create_file(self, path):
        """
        create a empty file
        :param path: xxx/xxx/xx.xx
        """
        if not self.exists(path):
            files = os.path.split(path)
            base_path = files[0]
            self.create_folder(base_path)
            os.mknod(path)

    def create_folder(self, path):
        """
        create  new folder or folders
        :param path: xxx/xxx/
        """
        if not os.path.exists(path):
            os.makedirs(path)

    def remove(self, file_path):
        """
        remove the file if this file is a folder and has some sub files
        will be removed
        :param file_path: file absolute path
        :return: True
        """
        if self.exists(file_path):
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path)

            return True
        else:
            return False

    def exists(self, file_path):
        """
        is file exists
        :param file_path:  file path
        :return: True/False
        """
        if os.path.exists(file_path):
            return True
        else:
            return False

    def read(self, file_path):
        """
        read the file content and return the content
        :param file_path: file absolute path
        :return:  file content
        """
        if not self.exists(file_path):
            return None
        file_temp = open(file_path, 'r')
        content = file_temp.read()
        return content

    def write(self, file_path, conent):
        """
        write the content to the file ,if the file not exists,it wil throw a exception
        :param file_path: file absolute path
        :param conent: the file content
        :return: True
        """

        if not self.exists(file_path):
            self.create_file(file_path)
        file = open(file_path, 'w')
        file.write(conent)
        file.flush()
        file.close()
        return True

    def rename(self, root_path, old_path, new_path):
        """
        rename the old path to the new path,if it is a file just rename the file name,
        but if it is a folder and has some sub folders, it will iterate all of them and
        move them to the folder
        :param root_path: root path
        :param old_path: old path
        :param new_path: new  path
        :return:
        """
        old_file_path = os.path.join(root_path, old_path)
        new_file_path = os.path.join(root_path, new_path)
        shutil.move(old_file_path, new_file_path)

    def all_file(self, file_path, is_dir=True, filter=None):
        """
        list all files in file path
        :param file_path: file absolute path
        :return: list
        """
        all_file = []
        for dir_path, dir_names, file_names in os.walk(file_path):
            if is_dir:
                for dir in dir_names:
                    all_file.append(os.path.join(dir_path, dir))
            for name in file_names:
                if filter:
                    dir_path = dir_path.replace(filter, "")

                all_file.append(os.path.join(dir_path, name))

        return all_file

    def workspace(self, path=None):
        """
        generate a workspace path like workspace is /home/workspace/ ,
        the path is test.py,then you can get /home/workspace/test.py
        :param path:
        :return:
        """
        workspace = self.cf.get("sys", "workspace")
        if not path:
            return workspace

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        if str(workspace).endswith("/"):
            return workspace + path
        else:
            return workspace + "/" + path

    def python3_cmd(self, pyfile):
        """
        configure python3 commands like 'python3 -u /home/workspace/xx.py'
        :param pyfile: the file absolute path /home/workspace/xxx.py
        :return: cmd to run the python file
        """

        return "python3 " + pyfile
