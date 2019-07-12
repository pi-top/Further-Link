# coding=utf-8
import logging

from flask_restplus import Namespace, Resource

from src.base.beanret import BeanRet
from src.rest.endpoints.serializers import bean

log = logging.getLogger(__name__)

ns_beatheart = Namespace(name='ping', description='check battery status and capacity')


@ns_beatheart.route("/")
class Beatheart(Resource):
    @ns_beatheart.marshal_with(bean)
    def get(self):
        '''
        ping beatheart check
        :return: BeanRet
        '''
        return BeanRet(success=True)
