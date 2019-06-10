# coding=utf-8
import json

"""
缓存数据对象
"""


class CacheData:
    def __init__(self, code=None, token=None, nat_port=None, server_addr=None, server_port=None, device_name=None):
        self.code = code
        self.token = token
        self.nat_port = nat_port
        self.server_addr = server_addr
        self.server_port = server_port
        self.device_name = device_name

    @property
    def getCode(self):
        return self.code

    def setCode(self, value):
        self.code = value

    @property
    def getToken(self):
        return self.token

    def setToken(self, value):
        self.token = value

    @property
    def getNatPort(self):
        return self.nat_port

    def setNatPort(self, value):
        self.nat_port = value

    @property
    def getServerAddr(self):
        return self.server_addr

    def setServerAddr(self, value):
        self.server_addr = value

    @property
    def getServerPort(self):
        return self.server_port

    def setServerPort(self, value):
        self.server_port = value

    @property
    def getDeviceName(self):
        return self.device_name

    def setDeviceName(self, value):
        self.device_name = value

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
