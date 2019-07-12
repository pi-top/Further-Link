# coding=utf-8
import hashlib
import json
import logging
import uuid

from src.base.cachedata import CacheData
from src.base.http import post
from src.base.serial_number import SerialNumber
from src.base.tools.cachedataclient import CacheDataClient
from src.service.basesv import BaseSV

log = logging.getLogger(__name__)


class SignInServerSV(BaseSV):
    def reg(self, ip, os, port=5000):
        '''
        register to server
        :return: oled token
        '''
        data = {
            "ip": str(ip),
            "port": str(port),
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
            device_name = data['codeName']
            cache_data = CacheData(str(code), str(token), str(device_name), serial_number=serial_number)
            CacheDataClient().write(cache_data.to_json())
            return token
        else:
            return None
