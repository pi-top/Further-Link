# coding=utf-8
import hashlib
import json
import logging
import os
import uuid

from diglett.base.cachedata import CacheData
from diglett.base.http import post, get
from diglett.base.serial_number import SerialNumber
from diglett.base.tools.cachedataclient import CacheDataClient
from diglett.service.basesv import BaseSV

log = logging.getLogger(__name__)


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

        serial_number = SerialNumber().serial_number()
        if not serial_number:
            cache_data = CacheDataClient().read()
            if cache_data:
                cache_data_obj = json.loads(cache_data, encoding="UTF-8")
                if cache_data_obj["serial_number"]:
                    serial_number = cache_data_obj["serial_number"]
                else:
                    serial_number = str(uuid.uuid1()).replace("-", "")
                    md5 = hashlib.md5()
                    serial_number_byte = serial_number.encode(encoding='utf-8')
                    md5.update(serial_number_byte)
                    serial_number = md5.hexdigest()
            else:
                serial_number = str(uuid.uuid1()).replace("-", "")
                md5 = hashlib.md5()
                serial_number_byte = serial_number.encode(encoding='utf-8')
                md5.update(serial_number_byte)
                serial_number = md5.hexdigest()

        data["serialNumber"] = serial_number

        url = self.regUri
        log.debug("reg to server [POST]===>" + url)
        log.debug(data)

        beanRet = post(url, data)
        log.debug(beanRet.to_json())

        # 缓存注册数据
        if beanRet.success:
            data = beanRet.data
            code = data['code']
            token = data['token']
            nat_port = data['natTraversePort']
            server_addr = data['natServerIp']
            server_port = data['natServerPort']
            device_name = data['codeName']
            cache_data = CacheData(str(code), str(token), str(nat_port), str(server_addr), str(server_port),
                                   str(device_name), serial_number=serial_number)
            CacheDataClient().write(cache_data.to_json())
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
            cache_data = CacheData().to_obj(CacheDataClient().read())
            file_temp = open(frp_ini, 'r')
            result = file_temp.read()
            log.info(result)
            result = result.replace('{{server_addr}}', cache_data.getServerAddr) \
                .replace('{{server_port}}', cache_data.getServerPort) \
                .replace('{{device_name}}', cache_data.getDeviceName) \
                .replace('{{nat_port}}', cache_data.getNatPort) \
                .replace("{{local_port}}", self.local_port)
            log.info(result)
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
            cache_data = CacheData().to_obj(CacheDataClient().read())
            url = self.pingUri.replace("{device_name}", cache_data.getDeviceName)
            beanRet = get(url)
            if beanRet.success:
                return True
            else:
                return False
        except Exception as e:
            log.error(e.message)
            return False

    def notify(self):
        '''
        通知上线成功
        :return:
        '''
        try:
            cache_data = CacheData().to_obj(CacheDataClient().read())
            domain = "null"
            # domain = self.pingUri.replace("{device_name}", cache_data.getDeviceName)
            url = self.notifyUri.replace("{code}", cache_data.code).replace("{domain}", domain)
            log.info(url)
            beanRet = get(url)
            if beanRet.success:
                return True
            else:
                return False
        except Exception as e:
            log.error(str(e.code) + e.message)
            return False
