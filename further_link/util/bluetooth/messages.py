from typing import Optional


class ChunkedMessageFormat:
    START = b"START-"
    STOP = b"STOP-"
    CHUNK_NUMBER_SIZE = 4
    CHUNK_DATA_SIZE = 508
    MAX_SIZE = 512


class Message:
    def __init__(self, data: Optional[bytearray] = None) -> None:
        self._message = bytearray()
        if data:
            self.append(data)

    @classmethod
    def from_string(cls, message: str):
        return Message(bytearray(message, "utf-8"))

    def as_bytearray(self) -> bytearray:
        return self._message

    def as_string(self) -> str:
        return str(self._message, "utf-8")

    @property
    def size(self) -> int:
        return len(self._message)

    def append(self, data: bytearray):
        self._message += data


class ChunkedMessage(Message):
    headers = {
        "START": bytearray(ChunkedMessageFormat.START),
        "STOP": bytearray(ChunkedMessageFormat.STOP),
    }

    def __init__(self, data: Optional[bytearray] = None) -> None:
        super().__init__()
        if data:
            self.append(data)

    @property
    def total_chunks(self) -> int:
        return (
            len(self.as_bytearray()) // ChunkedMessageFormat.CHUNK_DATA_SIZE + 1
        ) + 2

    @classmethod
    def from_long_message(cls, message: str):
        msg = Message.from_string(message)
        chunked = cls()
        total_chunks = (
            len(msg.as_bytearray()) // ChunkedMessageFormat.CHUNK_DATA_SIZE + 1
        )
        for i in range(total_chunks):
            chunk = bytearray(
                i.to_bytes(ChunkedMessageFormat.CHUNK_NUMBER_SIZE, byteorder="big")
            )
            chunk += bytearray(
                msg.as_bytearray()[
                    i
                    * ChunkedMessageFormat.CHUNK_DATA_SIZE : ChunkedMessageFormat.CHUNK_DATA_SIZE
                    * (i + 1)
                ]
            )
            chunked.append(chunk)
        return chunked

    @classmethod
    def is_start_message(cls, message: bytearray) -> bool:
        return message.startswith(bytearray(ChunkedMessageFormat.START))

    @classmethod
    def is_stop_message(cls, message: bytearray) -> bool:
        return message.startswith(bytearray(ChunkedMessageFormat.STOP))

    def chunk(self, index: int) -> bytearray:
        if index >= self.total_chunks or index < 0:
            raise Exception(
                f"Invalid chunk index {index} (total chunks: {self.total_chunks}))"
            )
        if index == 0:
            return bytearray(self.headers["START"])
        elif index == self.total_chunks - 1:
            return bytearray(self.headers["STOP"])

        index -= 1
        return (
            bytearray(
                index.to_bytes(ChunkedMessageFormat.CHUNK_NUMBER_SIZE, byteorder="big")
            )
            + self.as_bytearray()[
                index
                * ChunkedMessageFormat.CHUNK_DATA_SIZE : (index + 1)
                * ChunkedMessageFormat.CHUNK_DATA_SIZE
            ]
        )

    def append(self, data: bytearray):
        if self.is_start_message(data):
            self.headers["START"] = data
        elif self.is_stop_message(data):
            self.headers["STOP"] = data
        else:
            super().append(data[ChunkedMessageFormat.CHUNK_NUMBER_SIZE :])
