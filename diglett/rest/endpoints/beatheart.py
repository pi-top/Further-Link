# coding=utf-8
import logging

from flask_restplus import Namespace, Resource

from diglett.base.beanret import BeanRet

log = logging.getLogger(__name__)

ns_beatheart = Namespace(name='ping', description='check battery status and capacity')


@ns_beatheart.route("/")
class Beatheart(Resource):
    def get(self):
        '''
        ping beatheart check
        :return: BeanRet
        '''
        return BeanRet(success=True).to_json()
