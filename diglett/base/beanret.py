# coding=utf-8
import json

"""
return a json object like {"code":"0000","success":True,"info":"failed!","data":"{....}"}
"""


class BeanRet:
    def __init__(self, code="0000", success=False, info="failed", data=None):
        self.code = code
        self.success = success
        if success and info == 'failed':
            self.info = 'success'
        else:
            self.info = info
        self.data = data

    def to_json(self):
        '''
        obj to json str
        :return:
        '''
        return json.dumps(self.__dict__)

    def to_obj(self, value):
        '''
        str to obj
        '''
        self.__dict__ = json.loads(value)
        return self


if __name__ == '__main__':
    beanret = BeanRet()
    print(beanret.info)
    print(beanret.to_json())
    jsonStr = json.dumps(beanret.__dict__)
    print(jsonStr)
    beanretJson = json.loads(jsonStr)
    beanret2 = BeanRet()
    beanret2.to_obj(jsonStr)
