# coding=utf-8

"""
PUT 启动后的状态反馈与记录
"""
import os

from diglett.service.basesv import BaseSV


class BatterySV(BaseSV):
    def battery(self):
        '''
        监测电池状态
        1.获取电池信息
        2.判断电池状态
        3.提交电池信息

        Charging State: 0 电池待机状态
        Charging State: 1 电池充电状态
        Charging State: 2 电池充电状态且充满状态
        :return:
        '''
        state = 'Stateless'
        batteryCapacity = 0
        # 1.获取电池信息
        batteryStateList = os.popen(self.checkBatteryCommand).readlines()
        for batteryState in batteryStateList:
            # 获取电池电量
            if batteryState.startswith('Capacity:'):
                batteryCapacity = batteryState.replace('Capacity: ', '').replace('\n', '')

        for batteryState in batteryStateList:
            # 2.判断电池状态
            if "Charging State: 0\n" == batteryState:
                # Charging State: 0 电池待机状态
                state = 'Standby'
                break
            elif "Charging State: 1\n" == batteryState:
                # Charging State: 1 电池充电状态
                state = 'Charging'
                break
            elif "Charging State: 2\n" == batteryState:
                # 电池充电状态且充满状态
                state = 'FullyCharged'
                break
            else:
                # 无状态
                state = 'Stateless'
                break

        return batteryCapacity, state
