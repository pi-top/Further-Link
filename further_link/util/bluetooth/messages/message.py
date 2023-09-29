from typing import Optional


class Message:
    def __init__(self, data: Optional[bytearray] = None) -> None:
        if data is None:
            data = bytearray()
        self._data = data

    @classmethod
    def from_string(cls, message: str):
        return Message(bytearray(message, "utf-8"))

    def as_bytearray(self) -> bytearray:
        return self._data

    def as_string(self) -> str:
        return str(self._data, "utf-8")

    @property
    def size(self) -> int:
        return len(self._data)

    def append(self, data: bytearray):
        self._data += data
