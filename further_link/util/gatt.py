import logging
from queue import Queue
from threading import Thread
from time import sleep

from bluezero import adapter, async_tools, peripheral

PT_SERVICE_UUID = "12341000-1234-1234-1234-123456789abc"
PT_CHARACTERISTIC_UUID = "12341000-1234-1234-1234-123456789abd"
PT_DESCRIPTION_UUID = "12341000-1234-1234-1234-123456789abe"


# Encode strings before sending them
def to_byte_array(value):
    return [bytes(x, "utf-8") for x in str(value)]


# Decode received data into string
def decode_value(value):
    return str(value, "utf-8")


# Used in descriptors
def to_unicode_int_arr(message):
    return [ord(x) for x in message]


def get_bluetooth_device_address():
    devices = list(adapter.Adapter.available())
    if len(devices) == 0:
        raise Exception("No bluetooth devices found")
    return devices[0].address


class BluetoothInterface:
    def __init__(self) -> None:
        # Queues to handle messages
        self.out_queue: Queue = Queue()
        self.in_queue: Queue = Queue()

        # Gatt peripheral to interact with client
        self.gatt = GattPeripheral(
            address=get_bluetooth_device_address(),
            name="Further-Link",
            on_notify=self._notify,
            on_read=self._on_read,
            on_message=self._on_message,
        )

        self.gatt.start()

    async def close(self):
        return self.gatt.close()

    def send(self, message):
        self.out_queue.put(message)

    def read(self):
        return self.in_queue.get_nowait()

    def has_messages(self):
        return not self.in_queue.empty()

    def _notify(self, characteristic):
        while not self.out_queue.empty():
            message = self.out_queue.get()
            characteristic.set_value(to_byte_array({"message": message}))
            sleep(0.1)
        return characteristic.is_notifying

    def _on_read(self):
        return to_byte_array({"status": "alive!"})

    def _on_message(self, message, options):
        """
        Called when client sends a message
        """
        message = decode_value(message)
        self.in_queue.put(message)
        logging.info(f"Client message: {message}")


class GattPeripheral:
    def __init__(self, address, name, on_notify, on_read, on_message):
        self.address = address
        self.name = name
        self.peripheral = None
        self.on_notify = on_notify
        self.on_read = on_read
        self.on_message = on_message
        self._task = None

        self._setup()

    def start(self):
        self._task = Thread(target=self._run, daemon=True)
        self._task.start()

    def _run(self):
        if self.peripheral:
            # Publish peripheral and start event loop
            logging.info("Publishing GATT peripheral")
            self.peripheral.publish()
            logging.info("Stopped GATT peripheral")

    async def close(self):
        logging.info("Closing GATT peripheral")
        if self.peripheral:
            # bluezero peripherals don't have a 'stop/close' method; this is what gets run on exit
            # https://github.com/ukBaz/python-bluezero/blob/main/bluezero/peripheral.py#L147
            self.peripheral.mainloop.quit()
            self.peripheral.ad_manager.unregister_advertisement(self.peripheral.advert)

        if self._task and self._task.is_alive():
            # Wait for task to finish
            self._task.join()
            self._task = None

    def notify_callback(self, notifying, characteristic):
        """
        Noitificaton callback.

        :param notifying: boolean for start or stop of notifications
        :param characteristic: The python object for this characteristic
        """

        if notifying:
            async_tools.add_timer_seconds(0.1, self.on_notify, characteristic)

    def _setup(self):
        # Create peripheral
        logging.debug(
            f"Creating gatt peripheral with name {self.name} using address {self.address}"
        )
        self.peripheral = peripheral.Peripheral(
            self.address, local_name=self.name, appearance=1344
        )

        # Add service
        logging.debug(f"Adding service with UUID {PT_SERVICE_UUID}")
        self.peripheral.add_service(srv_id=1, uuid=PT_SERVICE_UUID, primary=True)

        # Add characteristic
        logging.debug(f"Adding characteristic with UUID {PT_CHARACTERISTIC_UUID}")
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=1,
            uuid=PT_CHARACTERISTIC_UUID,
            value=[],
            notifying=False,
            flags=["write", "read", "notify"],
            read_callback=self.on_read,
            write_callback=self.on_message,
            notify_callback=self.notify_callback,
        )

        # Add descriptor
        logging.debug(f"Adding descriptor with UUID {PT_DESCRIPTION_UUID}")
        self.peripheral.add_descriptor(
            srv_id=1,
            chr_id=1,
            dsc_id=1,
            uuid=PT_DESCRIPTION_UUID,
            value=to_unicode_int_arr(f"{self.name} messages"),
            flags=["read"],
        )
