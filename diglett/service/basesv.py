# coding=utf-8
import configparser

from settings import PITOP_CONF


class BaseSV:
    def __init__(self):
        cf = configparser.ConfigParser()
        cf.read(PITOP_CONF, encoding='UTF-8')
        host = cf.get("sys", "host")
        self.local_port = cf.get("sys", "local_port")
        self.group_code = cf.get("sys", "group_code")
        self.host = host
        # 获取电池信息指令
        self.checkBatteryCommand = 'pt-battery'
        # 注册设备
        self.regUri = self.host + '/devicePool/build.shtml'
        # 通知上线成功
        self.notifyUri = self.host + '/devicePool/notify.shtml?code={code}&domain={domain}'
