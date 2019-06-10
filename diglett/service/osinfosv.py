# coding=utf-8
import os

from diglett import logger


class OSInfoSV(object):
    def getIp(self):
        '''
        get eth0 ip
        get wlan0 ip
        :return:
        '''
        eths = os.popen("ip a|grep eth0|awk -Finet '{print $2}'|awk '{print $1}'").readlines()
        wlans = os.popen("ip a|grep wlan0|awk -Finet '{print $2}'|awk '{print $1}'").readlines()

        if eths.__len__() > 1:
            eth0 = eths[1]

        if wlans.__len__() > 1:
            wlan0 = wlans[1]
            if eths.__len__() <= 1:
                eth0 = wlans[1]
        else:
            wlan0 = '0.0.0.0/0'

        logger.info("eth0:" + eth0 + " wlan0:" + wlan0)
        return str(eth0).replace('\n', '').replace('\r', ''), str(wlan0).replace('\n', '').replace('\r', '')

    def getOSInfo(self):
        '''
        get os version
        :return:
        '''
        n = os.popen("uname -n").readlines()
        r = os.popen("uname -r").readlines()
        s = os.popen("uname -s").readlines()
        return (n[0] + " " + s[0] + " " + r[0]).replace("\n", "").replace('\r', '')
