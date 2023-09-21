from typing import Type

from .format import MessageFormat, PtMessageFormat


class Chunk:
    def __init__(
        self, formatted_data: bytearray, format: Type[MessageFormat] = PtMessageFormat
    ):
        """Representation of a chunk of data with a particular format. The 'format' object
        is used to retrieve information from the 'formatted_data' bytearray."""
        self.message = formatted_data
        self.format = format

        self.id = format.get_id(formatted_data)
        self.total_chunks = format.get_total_chunks(formatted_data)
        self.current_index = format.get_chunk_current_index(formatted_data)

    @classmethod
    def from_parameters(
        cls,
        id: int,
        current_index: int,
        total_chunks: int,
        data: bytearray,
        format: Type[MessageFormat],
    ):
        return cls(
            formatted_data=format.create_message(id, current_index, total_chunks, data),
            format=format,
        )

    def update_bytearray(self, arr):
        self.format.update_bytearray(arr, self.message)

    @property
    def payload(self):
        return self.format.get_payload(self.message)
