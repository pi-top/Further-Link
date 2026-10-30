MANUFACTURER = "pi-top"
MODEL_NUMBER = "pi-top [4]"
VENDOR_ID = 0x0A5C
PRODUCT_ID = 0x434C
SERIAL_NUMBER = "0000000000000000"
FIRMWARE_REVISION = "0.0.0"
HARDWARE_REVISION = "0.0.0"
SYSTEM_ID = "0000000000000000"
# Previously 0x0A5C which is Broadcom's vendor ID, not a valid GAP Appearance.
# Windows 11 validates appearance values and rejects/misidentifies invalid ones.
APPEARANCE = 0x0080  # Generic Computer (valid Bluetooth SIG assigned value)
