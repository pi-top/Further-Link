# coding=utf-8
import json

"""
return a json object like {"code":"0000","success":True,"info":"failed!","data":"{....}"}
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


if __name__ == '__main__':
    beanret = BeanRet()
    print(beanret.info)
    print(beanret.to_json())
    jsonStr = json.dumps(beanret.__dict__)
    print(jsonStr)
    beanretJson = json.loads(jsonStr)
    beanret2 = BeanRet()
    beanret2.to_obj(jsonStr)
