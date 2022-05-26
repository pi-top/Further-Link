from random import randint
from typing import List


class IdGenerator:
    used_ids: List
    MAX_VALUE: int

    def __init__(self, max_value: int) -> None:

        self.used_ids = []
        self.MAX_VALUE = max_value

    def create(self) -> int:
        if len(self.used_ids) == self.MAX_VALUE:
            raise Exception("All ids are in use.")

        candidate = randint(1, self.MAX_VALUE)
        while candidate in self.used_ids:
            candidate = randint(1, self.MAX_VALUE)
        self.used_ids.append(candidate)
        return candidate

    def free(self, id) -> None:
        if id in self.used_ids:
            self.used_ids.remove(id)
