# coding=utf-8
import os

from diglett.service.basesv import BaseSV


class BatterySV(BaseSV):
    def battery(self):
        '''
        check battery status
        1.get the battery info
        2.check the battery status

        Charging State: 0 Standby
        Charging State: 1 Charging
        Charging State: 2 FullyCharged
        :return:
        '''
        state = 'Stateless'
        batteryCapacity = 0
        # 1.get the battery info
        batteryStateList = os.popen(self.checkBatteryCommand).readlines()
        for batteryState in batteryStateList:
            if batteryState.startswith('Capacity:'):
                batteryCapacity = batteryState.replace('Capacity: ', '').replace('\n', '')

        for batteryState in batteryStateList:
            # 2.check the battery status
            if "Charging State: 0\n" == batteryState:
                # Charging State: 0
                state = 'Standby'
                break
            elif "Charging State: 1\n" == batteryState:
                # Charging State: 1
                state = 'Charging'
                break
            elif "Charging State: 2\n" == batteryState:
                # Charging State: 2
                state = 'FullyCharged'
                break
            else:
                state = 'Stateless'
                break

        return batteryCapacity, state
