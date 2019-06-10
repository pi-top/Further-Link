# coding=utf-8
import json

"""
返回数据的封装对象，可以进行json化转化与返回
"""


class BeanRet:
    def __init__(self, code="0000", success=False, info="操作失败", data=None):
        self.code = code
        self.success = success
        if success and info == '操作失败':
            self.info = '操作成功'
        else:
            self.info = info
        self.data = data

    @property
    def getSuccess(self):
        return self.success

    @getSuccess.setter
    def setSuccess(self, value):
        self.success = value

    @property
    def getInfo(self):
        return self.info

    @getInfo.setter
    def setInfo(self, value):
        self.info = value

    @property
    def getData(self):
        return self.data

    @getData.setter
    def setData(self, value):
        self.data = value

    @property
    def getCode(self):
        return self.code

    @getCode.setter
    def setCode(self, value):
        self.code = value

    def toJson(self):
        '''
        json序列化
        :return:json字符串
        '''
        return json.dumps(self.__dict__)

    def toObj(self, value):
        '''
        转化成beanret对象
        :param value:json字符串
        :return:BeanRet对象
        '''
        self.__dict__ = json.loads(value)
        return self


if __name__ == '__main__':
    beanret = BeanRet()
    print(beanret.getData)
    print(beanret.getSuccess)
    print(beanret.getInfo)
    print(beanret.toJson())
    jsonStr = json.dumps(beanret.__dict__)
    print(jsonStr)
    beanretJson = json.loads(jsonStr)
    beanret2 = BeanRet()
    beanret2.toObj(jsonStr)
    print(beanret2.getInfo)
