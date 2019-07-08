# coding=utf-8
import configparser

from diglett import app


class SerialNumber:
    def serial_number(self):
        """
        get the serial number from hub
        :return:
        """
        try:
            from ptcommon.i2c_device import I2CDevice
            cf = configparser.ConfigParser()
            cf.read(app.config['PITOP_CONF'])
            i2c_device = I2CDevice("/dev/i2c-1", 0x10)
            i2c_device.set_delays(0.001, 0.001)
            i2c_device.connect()
            sn_hex = i2c_device.read_n_unsigned_bytes(0xE7, 4, False)
            i2c_device.disconnect()
            if sn_hex:
                sn = str(hex(sn_hex)).replace('0x', '')
                return sn
        except:
            return None


if __name__ == '__main__':
    sn = SerialNumber().serial_number()
    print(sn)
