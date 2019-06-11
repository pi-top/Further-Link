# coding=utf-8
import logging

from flask_restplus import Namespace, Resource, fields

from diglett.base.beanret import BeanRet

log = logging.getLogger(__name__)

ns_pitop = Namespace(name='battery', description='Describes the operations related with the teams')

@ns_pitop.route('/')
class Battery(Resource):
    def get(self):
        '''
        ping 心跳检测
        :return: BeanRet
        '''
        return BeanRet(success=True, data={"capacity": 100, "state": "Full"}).toJson()
