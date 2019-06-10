# coding=utf-8
import os

from support import logger
from support.base.cachedata import CacheData
from support.base.http import post, get
from support.base.serial_number import SerialNumber
from support.base.tools.cachedataclient import CacheDataClient
from support.service.basesv import BaseSV


class SignInServerSV(BaseSV):
    def reg(self, ip, os):
        '''
        向服务器注册
        :return:
        '''
        data = {
            "ip": str(ip),
            "os": str(os),
            "groupCode": str(self.group_code)
        }
        # TODO 增加读取序列号的接口
        serial_number = "999999"
        # serial_number = SerialNumber().serial_number()
        if serial_number:
            data["serialNumber"] = serial_number

        url = self.regUri
        logger.info("reg to server [POST]===>" + url)
        logger.info(data)

        beanRet = post(url, data)
        logger.info(beanRet.toJson())

        # 缓存注册数据
        if beanRet.success:
            data = beanRet.getData
            code = data['code']
            token = data['token']
            nat_port = data['natTraversePort']
            server_addr = data['natServerIp']
            server_port = data['natServerPort']
            device_name = data['codeName']
            cache_data = CacheData(str(code), str(token), str(nat_port), str(server_addr), str(server_port),
                                   str(device_name))
            CacheDataClient().write(cache_data.toJson())
            return True, token
        else:
            return False, None

    def gen_nat_config(self, frp_ini):
        '''
        生成配置文件
        1.生成内网穿透的配置文件
        2.启动内网穿透客户端
        :return:
        '''
        try:
            # 1.生成内网穿透的配置文件
            cache_data = CacheData().toObj(CacheDataClient().read())
            file_temp = open(frp_ini, 'r')
            result = file_temp.read()
            logger.info(result)
            result = result.replace('{{server_addr}}', cache_data.getServerAddr) \
                .replace('{{server_port}}', cache_data.getServerPort) \
                .replace('{{device_name}}', cache_data.getDeviceName) \
                .replace('{{nat_port}}', cache_data.getNatPort) \
                .replace("{{local_port}}", self.local_port)
            logger.info(result)
            file = open("/etc/frp.ini", 'w')
            file.write(result)
            file.flush()

            # 2.启动内网穿透客户端
            os.system("bash /usr/local/frp/frpc.sh")

            return True
        except Exception as e:
            return False

    def check_nat_runing(self):
        '''
        检测内网穿透是否成功
        :return:
        '''
        try:
            cache_data = CacheData().toObj(CacheDataClient().read())
            url = self.pingUri.replace("{device_name}", cache_data.getDeviceName)
            beanRet = get(url)
            if beanRet.success:
                return True
            else:
                return False
        except Exception as e:
            logger.error(e.message)
            return False

    def notify(self):
        '''
        通知上线成功
        :return:
        '''
        try:
            cache_data = CacheData().toObj(CacheDataClient().read())
            domain = self.pingUri.replace("{device_name}", cache_data.getDeviceName)
            url = self.notifyUri.replace("{code}", cache_data.getCode).replace("{domain}", domain)
            logger.info(url)
            beanRet = get(url)
            if beanRet.success:
                return True
            else:
                return False
        except Exception as e:
            logger.error(str(e.code) + e.message)
            return False
