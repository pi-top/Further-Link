import logging

import click

from .bluetooth.utils import get_bluetooth_server_name
from .sdk import run_command


@click.command()
def set_pretty_hostname() -> None:
    try:
        name = get_bluetooth_server_name()
        run_command(f"hostnamectl set-hostname --pretty {name}")
    except Exception as e:
        logging.error(f"Error setting pretty hostname: {e}")
