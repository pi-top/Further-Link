# coding=utf-8
import logging

from flask_restplus import Namespace, Resource

from diglett.base.beanret import BeanRet
from diglett.rest.endpoints.serializers import bean
from diglett.service.batterysv import BatterySV

log = logging.getLogger(__name__)

ns_battery = Namespace(name='battery', description='check battery status and capacity')


@ns_battery.route('/')
class Battery(Resource):
    @ns_battery.marshal_with(bean)
    def get(self):
        '''
        battery check
        :return: BeanRet
        '''
        batteryCapacity, state = BatterySV().battery()
        return BeanRet(success=True, data={"capacity": batteryCapacity, "state": state})
