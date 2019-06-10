# coding=utf-8
"""
心跳检测
"""

from flask import Blueprint

from diglett import logger
from diglett.base.beanret import BeanRet
from diglett.service.batterysv import BatterySV

pitop = Blueprint('battery', __name__)

ws = Blueprint('wsbattery', __name__)

# 全局ws变量
batteryWebSocket = None


@ws.route('/battery.ws')
def wsKeyboard(socket):
    global batteryWebSocket
    batteryWebSocket = socket
    while not socket.closed:
        message = socket.receive()
        if not message:
            logger.info(str(message))


@pitop.route('/battery.shtml')
def battery():
    '''
    ping 心跳检测
    :return: BeanRet
    '''
    batteryCapacity, state = BatterySV().battery()
    return BeanRet(success=True, data={"capacity": batteryCapacity, "state": state}).toJson()
