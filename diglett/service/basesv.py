# coding=utf-8
import configparser

from settings import PITOP_CONF


class BaseSV:
    def __init__(self):
        cf = configparser.ConfigParser()
        cf.read(PITOP_CONF, encoding='UTF-8')
        host = cf.get("sys", "host")
        nat_check_url = cf.get("sys", "nat_check_url")
        self.local_port = cf.get("sys", "local_port")
        self.natConfigFile = cf.get("sys", "nat_config_file")
        self.group_code = cf.get("sys", "group_code")
        self.host = host
        # 获取电池信息指令
        self.checkBatteryCommand = 'pt-battery'
        # 注册设备
        self.regUri = self.host + '/devicePool/build.shtml'
        # 通知上线成功
        self.notifyUri = self.host + '/devicePool/notify.shtml?code={code}&domain={domain}'
        # 检测穿透接口
        self.pingUri = nat_check_url
