# coding=utf-8
from diglett import app
from diglett.base.cachedata import CacheData

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
        file = open(self.cachePath, 'r')
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

    def readAndWrite(self, cacheDataObj):
        '''
        根据CacheData对象进行增量保存
        :param cacheDataObj: CacheData的对象
        :return:
        '''
        cacheData = CacheData().toObj(self.read())
        if cacheDataObj.getJobnumber:
            cacheData.setJobnumber(cacheDataObj.getJobnumber)
        if cacheDataObj.getSN:
            cacheData.setSN(cacheDataObj.getSN)
        if cacheDataObj.getSampleCode:
            cacheData.setSN(cacheDataObj.getSampleCode)

        file = open(self.cachePath, 'w')
        file.write(cacheData.toJson())
        file.flush()


if __name__ == '__main__':
    CacheDataClient().write("dddddd")
