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

    def to_json(self):
        '''
        json序列化
        :return:json字符串
        '''
        return json.dumps(self.__dict__)

    def to_obj(self, value):
        '''
        转化成beanret对象
        :param value:json字符串
        :return:BeanRet对象
        '''
        self.__dict__ = json.loads(value)
        return self
