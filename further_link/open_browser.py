import json
from os import getenv

from pitop.common.command_runner import run_command, run_command_background


def get_serial_number_string(json_data):
    try:
        serial_number = json_data["primary"]
    except KeyError:
        return ""

    return "serial_number=" + str(serial_number)


def get_device_id_string(json_data):
    try:
        device_str = run_command(
            "cat /etc/pi-top/pt-device-manager/device_version", 1000
        )
    except KeyError:
        return ""

    return "device=" + str(device_str).strip()


def get_further_url():
    base_further_url = "https://further.pi-top.com/start"

    try:
        with open("/etc/pi-top/device_serial_numbers.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        return base_further_url

    further_url = base_further_url

    serial_string = get_serial_number_string(data)
    device_string = get_device_id_string(data)
    if serial_string != "" or device_string != "":
        further_url += "?"
        if serial_string != "":
            further_url += serial_string
            if device_string != "":
                further_url += "&"

        if device_string != "":
            further_url += device_string

    return further_url


def get_chromium_command(further_url):
    sudo_user = getenv("SUDO_USER")
    if sudo_user is not None:
        cmd = f'su {sudo_user} -c "chromium-browser --new-window --start-maximized {further_url}"'
    else:
        cmd = f"chromium-browser --new-window --start-maximized {further_url}"
    return cmd


def open_further_in_background():
    run_command_background(get_chromium_command(get_further_url()))
