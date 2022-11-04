import os
from random import randint
from typing import List


class IdGenerator:
    used_ids: List
    MIN_VALUE: int
    MAX_VALUE: int

    def __init__(self, max_value: int, min_value: int = 1) -> None:

        self.used_ids = []
        self.MIN_VALUE = min_value
        self.MAX_VALUE = max_value

    def has_ids(self) -> bool:
        return len(self.used_ids) < self.MAX_VALUE - self.MIN_VALUE + 1

    def create(self) -> int:
        if not self.has_ids():
            raise Exception("All ids are in use.")

        candidate = randint(self.MIN_VALUE, self.MAX_VALUE)
        while candidate in self.used_ids:
            candidate = randint(self.MIN_VALUE, self.MAX_VALUE)
        self.used_ids.append(candidate)
        return candidate

    def free(self, id) -> None:
        if id in self.used_ids:
            self.used_ids.remove(id)


# each run will need a unique id
# one use of the id is for the pt-web-vnc virtual display id and port numbers
# so we must use +ve int < 1000, with 0-99 reserved for other uses
# envvar FURTHER_LINK_MAX_PROCESSES can be used to limit the range
var_max_processes = os.environ.get("FURTHER_LINK_MAX_PROCESSES")
MAX = 900
if isinstance(var_max_processes, str) and var_max_processes.isdigit():
    max_processes = int(var_max_processes)
else:
    max_processes = MAX
if 1 > max_processes > MAX:
    max_processes = MAX


# global "singleton"
id_generator = IdGenerator(min_value=100, max_value=99 + max_processes)
