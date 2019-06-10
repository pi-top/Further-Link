# coding=utf-8
"""
心跳检测
"""

from flask import Blueprint, render_template

from support import logger
from support.base.beanret import BeanRet
from support.base.cachedata import CacheData
from support.base.tools.cachedataclient import CacheDataClient

pitop = Blueprint('beatheart', __name__)


@pitop.route('/ping.shtml')
def ping():
    '''
    ping 心跳检测
    :return: BeanRet
    '''

    return BeanRet(success=True).toJson()


@pitop.route('/config.shtml')
def config():
    '''
    ping 心跳检测
    :return: BeanRet
    '''
    cache_data = CacheData().toObj(CacheDataClient().read())
    data = {
        'server_addr': cache_data.getServerAddr,
        'server_port': cache_data.getServerPort,
        'nat_port': cache_data.getNatPort,
        'device_name': cache_data.getDeviceName
    }
    result = str(render_template('frp.ini', **data))
    logger.info(result)

    file = open("/etc/frp.ini", 'w')
    file.write(result)
    file.flush()
    return BeanRet(success=True).toJson()
