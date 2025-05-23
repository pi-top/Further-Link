import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Union

from bluez_peripheral.gatt.characteristic import characteristic
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.uuid16 import UUID16


def bytearray_to_dict(message: bytearray) -> Dict:
    message_str = message.decode()

    # remove trailing commas
    message_str = re.sub(",[ \t\r\n]+}", "}", message_str)
    message_str = re.sub(",[ \t\r\n]+]", "]", message_str)

    return json.loads(message_str)


def get_raspberry_pi_serial() -> str:
    serial = ""
    cpu_info_file = "/proc/cpuinfo"

    if not Path(cpu_info_file).exists():
        return serial

    try:
        with open(cpu_info_file) as fd:
            for line in fd:
                if line.startswith("Serial"):
                    serial = line.rpartition(":")[2].strip().upper()
                    break
    except Exception:
        serial = ""
    return serial


def get_bluetooth_server_name() -> str:
    try:
        id = get_raspberry_pi_serial()[-4:]
    except Exception:
        id = "0000"
    return f"pi-top-{id}"


def find_object_with_uuid(
    obj_arr: list[Union[Service, characteristic]], uuid: str
) -> Optional[Union[Service, characteristic]]:
    uuid16 = UUID16.parse_uuid(uuid)
    for obj in obj_arr:
        if not hasattr(obj, "UUID"):
            logging.debug(f"Object {obj} does not have UUID attribute, skipping...")
            continue
        if obj.UUID == str(uuid16):
            return obj
    return None


async def is_bt_card_blocked() -> bool:
    """Check if the BT card is blocked by checking if the adapter is powered on."""
    cmd = "rfkill list bluetooth -o Soft -n"
    try:
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip() == "blocked"
    except Exception as e:
        logging.error(f"Error checking if BT card is blocked: {e}")
        return False


async def unlock_bt_card() -> None:
    """Unlock the BT card using rfkill"""
    command = "rfkill unblock bluetooth"
    logging.info(f"Unlocking BT card using command: {command}")
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
    except Exception as e:
        logging.error(f"Error unlocking BT card: {e}")
