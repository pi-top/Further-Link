from os import environ, getenv
from shlex import split
from subprocess import DEVNULL, Popen

import click


def run_command_background(command_str, print_output=False):
    env = environ.copy()
    env["DISPLAY"] = ":0"
    return Popen(
        split(command_str),
        env=env,
        stderr=None if print_output else DEVNULL,
        stdout=None if print_output else DEVNULL,
    )


def get_further_url():
    further_url = "https://further.pi-top.com/start"

    with open("/run/pt_hub_serial", "r") as f:
        serial = f.read().strip()

    with open("/run/pt_device_type", "r") as f:
        device = f.read().strip()

    if serial or device:
        further_url += "?"

        if serial:
            further_url += f"serial_number={serial}"

        if serial and device:
            further_url += "&"

        if device:
            further_url += f"device={serial}"

    return further_url


def get_chromium_command(further_url):
    sudo_user = getenv("SUDO_USER")
    if sudo_user is not None:
        cmd = f'su {sudo_user} -c "chromium-browser --new-window --start-maximized {further_url}"'
    else:
        cmd = f"chromium-browser --new-window --start-maximized {further_url}"
    return cmd


@click.command()
@click.option("--print-only", is_flag=True)
@click.version_option()
def start_further(print_only):
    url = get_further_url()

    if print_only:
        print(url)
        return

    run_command_background(get_chromium_command(url))
