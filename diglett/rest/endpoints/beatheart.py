# coding=utf-8
import logging

from flask_restplus import Namespace, Resource

from diglett.base.beanret import BeanRet
from diglett.entity.tree_vo import TreeVO
from diglett.rest.endpoints.serializers import bean

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
