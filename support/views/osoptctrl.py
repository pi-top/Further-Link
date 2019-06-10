#!/usr/bin/env python
# coding=utf-8
import linecache
import os
import _thread
import time

from flask import Blueprint

from support import logger
from support.base.beanret import BeanRet

pitop = Blueprint('osopt', __name__)


def os_reboot(reboot):
    logger.info("start _thread to stop OS" + reboot)
    time.sleep(3)
    os.system("init 6")


def os_close():
    logger.info("start _thread to stop OS close")
    time.sleep(3)
    os.system("init 0")


@pitop.route('/reboot')
def reboot():
    try:
        _thread.start_new_thread(os_reboot, ("reboot",))
    except:
        logger.error("Error: unable to start _thread")
    return BeanRet(success=True).toJson()


@pitop.route('/close')
def close():
    # try:
    #     _thread.start_new_thread(os_close, ())
    # except:
    #     logger.error("Error: unable to start _thread")
    return BeanRet(success=True).toJson()


@pitop.route('/log/read/<linenum>')
def readlogs(linenum):
    '''
    根据行号读取linux日志
    :param linenum:
    :return:
    '''
    logfile = "/var/log/messages"
    log = linecache.getline(logfile, int(linenum))
    if log.__len__() > 0:
        return BeanRet(success=True, data=log).toJson()
    else:
        return BeanRet(success=False).toJson()


@pitop.route('/log/count/lines')
def logCountLines():
    '''
    count linux os log messages
    :return:
    '''
    logfile = "/var/log/messages"
    count = 0
    thefile = open(logfile, 'rb')
    while True:
        buffer = thefile.read(8192 * 1024)
        if not buffer:
            break
        count += buffer.count('\n')
    thefile.close()
    return BeanRet(success=True, data=count).toJson()


@pitop.route('/cpu/mem')
def cpuMem():
    '''
    read mem & cpu
    :return:
    '''
    totalMem = os.popen("free -m|grep Mem|awk '{print $2}'").readlines()
    totalMem = str(totalMem[0]).replace("\n", "")
    usedMem = os.popen("free -m|grep Mem|awk '{print $3}'").readlines()
    usedMem = str(usedMem[0]).replace("\n", "")
    freeMem = os.popen("free -m|grep Mem|awk '{print $4}'").readlines()
    freeMem = str(freeMem[0]).replace("\n", "")
    cpu = os.popen("vmstat 1 2|grep 1|awk '{print $15}'").readlines()
    cpu = str(cpu[1]).replace('\n', '')

    return BeanRet(success=True,
                   data={"cpu": cpu, "totalMem": totalMem, "userdMem": usedMem, "freeMem": freeMem}).toJson()
