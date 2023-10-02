from typing import Dict, Type

from .chunk import Chunk
from .format import MessageFormat
from .message import Message


class ChunkedMessage:
    def __init__(self, id: int) -> None:
        self.id = id
        self._data = bytearray(0)
        self.total_chunks = 0
        self._chunks: Dict[int, Chunk] = {}

    @property
    def received_chunks(self) -> int:
        return len(self._chunks.keys())

    def is_complete(self) -> bool:
        return self.total_chunks == self.received_chunks

    def append(self, chunk: Chunk) -> None:
        if chunk.id != self.id:
            raise Exception(
                f"Provided chunk with id {chunk.id} doesn't belong to ChunkedMessage with id {self.id}"
            )

        if self._chunks.get(chunk.current_index) is not None:
            # already received this chunk
            return

        self._chunks[chunk.current_index] = chunk
        if self.total_chunks == 0:
            self.total_chunks = chunk.total_chunks
            # create empty bytearray of the correct size.
            self._data = bytearray(self.total_chunks)

        # Update data with received chunk
        chunk.update_bytearray(self._data)

    def get_chunk(self, index: int) -> Chunk:
        if index >= self.received_chunks or index < 0:
            raise Exception(
                f"Invalid chunk index {index} (total chunks: {self.received_chunks}))"
            )
        if index not in self._chunks:
            raise Exception(f"Chunk of index {index} doesn't exist.")
        return self._chunks[index]

    def as_bytearray(self) -> bytearray:
        return self._data

    def as_string(self) -> str:
        return self.as_bytearray().decode()

    @classmethod
    def from_bytearray(cls, id: int, message: bytearray, format: Type[MessageFormat]):
        assert isinstance(message, bytearray)
        return cls.from_message(id, Message(message), format)

    @classmethod
    def from_string(cls, id: int, message: str, format: Type[MessageFormat]):
        assert isinstance(message, str)
        return cls.from_message(id, Message.from_string(message), format)

    @classmethod
    def from_chunk(cls, chunk: Chunk, format: Type[MessageFormat]):
        print(f"from chunk : id: {chunk.id}, message: {chunk.payload}")
        obj = cls(chunk.id)
        obj.total_chunks = chunk.total_chunks
        obj._data = bytearray(obj.total_chunks)
        chunk.update_bytearray(obj._data)
        return obj

    @classmethod
    def from_message(cls, id: int, message: Message, format: Type[MessageFormat]):
        chunked = cls(id)
        required_chunks = format.get_number_of_chunks_for_message(message)

        for i in range(required_chunks):
            data = bytearray(
                message.as_bytearray()[
                    i * format.DATA_SIZE : format.DATA_SIZE * (i + 1)
                ]
            )
            chunk = Chunk.from_parameters(
                id=id,
                current_index=i,
                total_chunks=required_chunks,
                data=data,
                format=format,
            )
            chunked.append(chunk)
        return chunked
