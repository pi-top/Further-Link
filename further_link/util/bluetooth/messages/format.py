from .message import Message


class MessageFormat:
    MAX_SIZE = 512
    DATA_SIZE = 504

    @classmethod
    def create_message(
        cls, id: int, current_index: int, total_chunks: int, data: bytearray
    ) -> bytearray:
        raise NotImplementedError()

    @classmethod
    def update_bytearray(cls, arr: bytearray, formatted_data: bytearray):
        raise NotImplementedError()

    @classmethod
    def get_id(cls, formatted_data: bytearray) -> int:
        raise NotImplementedError()

    @classmethod
    def get_chunk_current_index(cls, formatted_data: bytearray) -> int:
        raise NotImplementedError()

    @classmethod
    def get_payload(cls, formatted_data: bytearray) -> bytearray:
        raise NotImplementedError()

    @classmethod
    def get_complete_message_size(cls, formatted_data: bytearray) -> int:
        raise NotImplementedError()

    @classmethod
    def get_number_of_chunks_for_message(cls, message: Message) -> int:
        raise NotImplementedError()

    @classmethod
    def get_total_chunks(cls, formatted_data: bytearray) -> int:
        raise NotImplementedError()


class PtMessageFormat(MessageFormat):
    CHUNK_MESSAGE_ID_SIZE = 2
    CHUNK_END_INDEX_SIZE = 3
    CHUNK_CURRENT_INDEX_SIZE = 3
    DATA_SIZE = 504

    @classmethod
    def create_message(
        cls, id: int, current_index: int, total_chunks: int, data: bytearray
    ) -> bytearray:
        return bytearray(
            int.to_bytes(id, cls.CHUNK_MESSAGE_ID_SIZE, byteorder="little")
            + int.to_bytes(
                total_chunks - 1, cls.CHUNK_END_INDEX_SIZE, byteorder="little"
            )
            + int.to_bytes(
                current_index, cls.CHUNK_CURRENT_INDEX_SIZE, byteorder="little"
            )
            + data
        )

    @classmethod
    def get_id(cls, formatted_data: bytearray) -> int:
        id_bytes = formatted_data[: cls.CHUNK_MESSAGE_ID_SIZE]
        return int.from_bytes(id_bytes, byteorder="little")

    @classmethod
    def get_chunk_end_index(cls, formatted_data: bytearray) -> int:
        end_index_bytes = formatted_data[
            cls.CHUNK_MESSAGE_ID_SIZE : cls.CHUNK_MESSAGE_ID_SIZE
            + cls.CHUNK_END_INDEX_SIZE
        ]
        return int.from_bytes(end_index_bytes, byteorder="little")

    @classmethod
    def get_chunk_current_index(cls, formatted_data: bytearray) -> int:
        current_index_bytes = formatted_data[
            cls.CHUNK_MESSAGE_ID_SIZE
            + cls.CHUNK_END_INDEX_SIZE : cls.CHUNK_MESSAGE_ID_SIZE
            + cls.CHUNK_END_INDEX_SIZE
            + cls.CHUNK_CURRENT_INDEX_SIZE
        ]
        return int.from_bytes(current_index_bytes, byteorder="little")

    @classmethod
    def get_payload(cls, formatted_data: bytearray) -> bytearray:
        return formatted_data[
            cls.CHUNK_MESSAGE_ID_SIZE
            + cls.CHUNK_END_INDEX_SIZE
            + cls.CHUNK_CURRENT_INDEX_SIZE :
        ]

    @classmethod
    def get_complete_message_size(cls, formatted_data: bytearray) -> int:
        return cls.DATA_SIZE * cls.get_chunk_end_index(formatted_data)

    @classmethod
    def get_number_of_chunks_for_message(cls, message: Message) -> int:
        return len(message.as_bytearray()) // cls.DATA_SIZE + 1

    @classmethod
    def update_bytearray(cls, arr: bytearray, formatted_data: bytearray):
        current_index = cls.get_chunk_current_index(formatted_data)
        arr[
            cls.DATA_SIZE * current_index : current_index * cls.DATA_SIZE
            + cls.DATA_SIZE
        ] = cls.get_payload(formatted_data)

    @classmethod
    def get_total_chunks(cls, formatted_data: bytearray) -> int:
        return cls.get_chunk_end_index(formatted_data) + 1
