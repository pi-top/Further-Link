# Mocks https://github.com/spacecheese/bluez_peripheral/blob/master/bluez_peripheral/gatt/characteristic.py
import inspect
import logging
from typing import Callable


class characteristicMock:
    _INTERFACE = "org.bluez.GattCharacteristic1"

    def __init__(
        self,
        uuid,
        flags,
    ):
        self.uuid = uuid
        self.getter_func = None
        self.setter_func = None
        self.flags = flags

        self._notify = False
        self._service_path = None
        self._descriptors = []
        self._service = None
        self._value = bytearray()

        self.callbacks = []

    def _subscribe(self, callback: Callable):
        self.callbacks.append(callback)

    def changed(self, new_value: bytes):
        self._value = bytearray(new_value)
        for callback in self.callbacks:
            callback(new_value)

    # Decorators
    def setter(self, setter_func):
        self.setter_func = setter_func
        return self

    def __call__(
        self,
        getter_func=None,
        setter_func=None,
    ):
        self.getter_func = getter_func
        self.setter_func = setter_func
        return self

    def _is_registered(self):
        return self._service_path is not None

    def _set_service(self, service):
        self._service = service

        for desc in self._descriptors:
            desc._set_service(service)

    def _get_path(self) -> str:
        return self._service_path + "/char{:d}".format(self._num)

    def _export(self, bus, service_path: str, num: int):
        self._service_path = service_path
        self._num = num
        bus.export(self._get_path(), self)

        # Export and number each of the child descriptors.
        i = 0
        for desc in self._descriptors:
            desc._export(bus, self._get_path(), i)
            i += 1

    def _unexport(self, bus):
        # Unexport this and each of the child descriptors.
        bus.unexport(self._get_path(), self._INTERFACE)
        for desc in self._descriptors:
            desc._unexport(bus)

        self._service_path = None

    async def ReadValue(self, options):
        try:
            res = []
            if inspect.iscoroutinefunction(self.getter_func):
                res = await self.getter_func(self._service, options)
            else:
                res = self.getter_func(self._service, options)

            if res is not None:
                self._value = bytearray(res)

            return bytes(self._value)
        except Exception as e:
            logging.error(f"Error: {e}")
            raise e

    async def WriteValue(self, data, options):
        opts = options
        try:
            if inspect.iscoroutinefunction(self.setter_func):
                await self.setter_func(self._service, data, opts)
            else:
                self.setter_func(self._service, data, opts)
        except Exception as e:
            logging.error(f"Error: {e}")
            raise e
        self._value = bytearray(data)

    def StartNotify(self):
        self._notify = True

    def StopNotify(self):
        self._notify = False

    @property
    def UUID(self):
        return str(self.uuid)

    @property
    def Service(self):
        return self._service_path

    @property
    def Flags(self):
        return []

    @property
    def Value(self):
        return bytes(self._value)
