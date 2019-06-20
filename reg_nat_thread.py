# coding=utf-8
import configparser
import threading
import time

from diglett import app
from diglett import logger
from diglett.base.http import get
from diglett.base.oled_token import Token
from diglett.service.osinfosv import OSInfoSV
from diglett.service.signInServer import SignInServerSV


class RegNat(threading.Thread):
    def __init__(self, local_port=5000):
        threading.Thread.__init__(self)
        self.local_port = local_port

    def run(self):
        is_ping = self.ping()
        if is_ping:
            self.reg()

    def ping(self):
        '''
        ping local server if it is running return True,after 10 times ping return False
        :return: True/False
        '''
        for i in range(10, 0, -1):
            time.sleep(2)
            beanret = get("http://127.0.0.1:" + str(self.local_port) + "/api/ping/")
            if beanret.success:
                return True
            elif i == 1:
                return False

    def reg(self):
        '''
        register to server get NAT infos from server,this step
        will build a tunnel for cloud and client,then cloud can
        manage this device via this tunnel
        '''
        # try:
        cf = configparser.ConfigParser()
        cf.read(app.config['PITOP_CONF'], encoding='UTF-8')
        display_token_time = cf.get("sys", "display_token_time")
        # 向服务器注册
        logger.info("reg to server")
        osInfo = OSInfoSV()
        eth0, wlan = osInfo.getIp()
        os = osInfo.getOSInfo()
        signInServerSV = SignInServerSV()
        flag, token = signInServerSV.reg(eth0, os)
        # if flag:
        #     logger.info("generate configure file")
        #     # 生成内网穿透配置文件
        #     frp_ini = app.config['FRP_INI']
        #     flag = signInServerSV.gen_nat_config(frp_ini)
        #     time.sleep(1)

        if flag:
            logger.info("notify server")
            signInServerSV.notify()

        oled = Token()
        oled.display(token)
        time.sleep(int(display_token_time))

        # except Exception as e:
        #     logger.error("reg to server failed")
