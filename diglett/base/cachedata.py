# coding=utf-8
import json

"""
the cache data object
"""


class CacheData:
    def __init__(self, code=None, token=None, nat_port=None, server_addr=None, server_port=None, device_name=None,
                 serial_number=None):
        self.code = code
        self.token = token
        self.nat_port = nat_port
        self.server_addr = server_addr
        self.server_port = server_port
        self.device_name = device_name
        self.serial_number = serial_number

    def to_json(self):
        """
        obj to json str
        """
        return json.dumps(self.__dict__)

    def to_obj(self, value):
        """
        str to obj
        """
        self.__dict__ = json.loads(value, encoding="UTF-8")
        return self
