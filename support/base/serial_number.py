# coding=utf-8

"""
DUT 启动后的状态反馈与记录
"""
import configparser

from ptcommon.i2c_device import I2CDevice

from support import app


class SerialNumber:
    def serial_number(self):
        '''
        获取系统的sn码并保存
        :return:
        '''
        try:

            cf = configparser.ConfigParser()
            cf.read(app.config['PITOP_CONF'])
            # hub地址
            self.hub_address = cf.get("sys", "hub_address")
            # 序列号地址
            self.serial_address = cf.get("sys", "serial_address")
            i2c_device = I2CDevice("/dev/i2c-1", self.hub_address)
            i2c_device.set_delays(0.001, 0.001)
            i2c_device.connect()
            sn_hex = i2c_device.read_n_unsigned_bytes(self.serial_address, 4, False)
            i2c_device.disconnect()
            if sn_hex:
                sn = str(hex(sn_hex)).replace('0x', '')
                return sn

        except:
            return None
