# coding=utf-8
import os

from diglett import app


class CacheDataClient(object):
    def __init__(self):
        self.cachePath = app.config['CACHEDATA_JSON']

    def read(self):
        '''
        read the cache data
        :return:json Data
        '''
        if not os.path.exists(self.cachePath):
            return None
        file = open(self.cachePath, 'r', encoding="UTF-8")
        jsonData = file.read()
        return jsonData

    def write(self, jsonData):
        '''
        write the data to json
        :param jsonData:json
        '''
        file = open(self.cachePath, 'w')
        file.write(jsonData)
        file.flush()


if __name__ == '__main__':
    CacheDataClient().write("dddddd")
