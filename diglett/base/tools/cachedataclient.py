# coding=utf-8
import os

from diglett import app

"""
缓存数据工具
"""


class CacheDataClient(object):
    def __init__(self):
        self.cachePath = app.config['CACHEDATA_JSON']

    def read(self):
        '''
        读取缓存
        :return:jsonData数据
        '''
        if not os.path.exists(self.cachePath):
            return None
        file = open(self.cachePath, 'r', encoding="UTF-8")
        jsonData = file.read()
        return jsonData

    def write(self, jsonData):
        '''
        写入缓存
        :param jsonData:json 格式数据
        '''
        file = open(self.cachePath, 'w')
        file.write(jsonData)
        file.flush()


if __name__ == '__main__':
    CacheDataClient().write("dddddd")
