import logging
from os import geteuid

import click

from further_link.util import state


def is_root() -> bool:
    return geteuid() == 0


def set_encryption(value: str) -> None:
    if not is_root():
        logging.error("This command must be run as root!")
        exit(1)

    value = value.lower()
    if value not in ("true", "1", "false", "0"):
        logging.error(
            "Value must be either 'true' or '1' to enable encryption or 'false' or '0' otherwise"
        )
        exit(1)

    logging.info(f"Setting further-link bluetooth GATT server encryption to '{value}'")
    state.set("bluetooth", "encrypt", value)


@click.command()
@click.argument("use_encryption", required=False)
def main(use_encryption):
    if use_encryption:
        set_encryption(use_encryption)
    else:
        print(state.get("bluetooth", "encrypt", "true"))


if __name__ == "__main__":
    main(prog_name="further-link-bluetooth-encryption")
