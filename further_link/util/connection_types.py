from enum import Enum


class ConnectionType(Enum):
    BLUETOOTH = 1
    WEBSOCKET = 2


bandwidth_limits_kBps = {
    ConnectionType.BLUETOOTH: 8,
    ConnectionType.WEBSOCKET: 128,
}
