import configparser

import os

import shutil

from support import app


class Singleton(object):
    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls)
        return cls._instance


"""
os.path.abspath(path) #返回绝对路径
os.path.basename(path) #返回文件名
os.path.commonprefix(list) #返回多个路径中，所有path共有的最长的路径。
os.path.dirname(path) #返回文件路径
os.path.exists(path)  #路径存在则返回True,路径损坏返回False
os.path.lexists  #路径存在则返回True,路径损坏也返回True
os.path.expanduser(path)  #把path中包含的"~"和"~user"转换成用户目录
os.path.expandvars(path)  #根据环境变量的值替换path中包含的”$name”和”${name}”
os.path.getatime(path)  #返回最后一次进入此path的时间。
os.path.getmtime(path)  #返回在此path下最后一次修改的时间。
os.path.getctime(path)  #返回path的大小
os.path.getsize(path)  #返回文件大小，如果文件不存在就返回错误
os.path.isabs(path)  #判断是否为绝对路径
os.path.isfile(path)  #判断路径是否为文件
os.path.isdir(path)  #判断路径是否为目录
os.path.islink(path)  #判断路径是否为链接
os.path.ismount(path)  #判断路径是否为挂载点（）
os.path.join(path1[, path2[, ...]])  #把目录和文件名合成一个路径
os.path.normcase(path)  #转换path的大小写和斜杠
os.path.normpath(path)  #规范path字符串形式
os.path.realpath(path)  #返回path的真实路径
os.path.relpath(path[, start])  #从start开始计算相对路径
os.path.samefile(path1, path2)  #判断目录或文件是否相同
os.path.sameopenfile(fp1, fp2)  #判断fp1和fp2是否指向同一文件
os.path.samestat(stat1, stat2)  #判断stat tuple stat1和stat2是否指向同一个文件
os.path.split(path)  #把路径分割成dirname和basename，返回一个元组
os.path.splitdrive(path)   #一般用在windows下，返回驱动器名和路径组成的元组
os.path.splitext(path)  #分割路径，返回路径名和文件扩展名的元组
os.path.splitunc(path)  #把路径分割为加载点与文件
os.path.walk(path, visit, arg)  #遍历path，进入每个目录都调用visit函数，visit函数必须有3个参数(arg, dirname, names)，dirname表示当前目录的目录名，names代表当前目录下的所有文件名，args则为walk的第三个参数
os.path.supports_unicode_filenames  #设置是否支持unicode路径名
"""


class FileTool(Singleton):
    def __init__(self):
        self.cf = configparser.ConfigParser()
        self.cf.read(app.config['PITOP_CONF'])

    def create_file(self, path):
        """
        create a empty file
        :param path: xxx/xxx/xx.xx
        :return:
        """
        if not self.exists(path):
            files = os.path.split(path)
            base_path = files[0]
            if not os.path.exists(base_path):
                os.makedirs(base_path)
            os.mknod(path)

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
            raise FileNotFoundError("check the file path,the file not exists!")

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
        :param root_path:
        :param old_path:
        :param new_path:
        :return:
        """
        old_file_path = os.path.join(root_path, old_path)
        new_file_path = os.path.join(root_path, new_path)
        list = []
        if os.path.isdir(old_file_path) and os.listdir(old_file_path).__len__() > 0:
            list_dirs = os.listdir(old_file_path)
            if list_dirs.__len__() > 0:
                old_file_list = self.all_file(old_file_path)
                shutil.move(old_file_path, new_file_path)
                new_file_list = self.all_file(new_file_path)
                for old_file in old_file_list:
                    for new_file in new_file_list:
                        if new_file.replace(new_path, old_path).__eq__(old_file):
                            list.append({"oldPath": old_file.replace(root_path, ""),
                                         "newPath": new_file.replace(root_path, "")})
        else:
            shutil.move(old_path, new_path)
            list.append({"oldPath": old_path, "newPath": new_path})

        return list

    def all_file(self, file_path):
        """
        list all files in file path
        :param file_path: file absolute path
        :return: list
        """
        all_file = []
        for dir_path, dir_names, file_names in os.walk(file_path):
            for dir in dir_names:
                all_file.append(os.path.join(dir_path, dir))
            for name in file_names:
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

        return "python3 -u " + pyfile
