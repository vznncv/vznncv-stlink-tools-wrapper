"""
Helper project to detect stlink devices.
"""
import re
from typing import NamedTuple, List

import usb.core
from cached_property import cached_property


class StLinkDeviceType(NamedTuple):
    version: str
    vendor_id: int
    product_id: int
    out_pipe: int
    in_pipe: int


_STLINK_DEVICE_TYPES = {(stlink_dev.vendor_id, stlink_dev.product_id): stlink_dev for stlink_dev in [
    StLinkDeviceType(version='V2', vendor_id=0x0483, product_id=0x3748, out_pipe=0x02, in_pipe=0x81),
    StLinkDeviceType(version='V2-1', vendor_id=0x0483, product_id=0x374b, out_pipe=0x01, in_pipe=0x81),
    # without MASS STORAGE
    StLinkDeviceType(version='V2-1', vendor_id=0x0483, product_id=0x3752, out_pipe=0x01, in_pipe=0x81),
    StLinkDeviceType(version='V3E', vendor_id=0x0483, product_id=0x374e, out_pipe=0x01, in_pipe=0x81),
    StLinkDeviceType(version='V3', vendor_id=0x0483, product_id=0x374f, out_pipe=0x01, in_pipe=0x81),
    # without MASS STORAGE
    StLinkDeviceType(version='v3', vendor_id=0x0483, product_id=0x3753, out_pipe=0x01, in_pipe=0x81),
]}


class StLinkDevice:
    def __init__(self, *, dev, type):
        self.dev: usb.core.Device = dev
        self.type: StLinkDeviceType = type

    _SERIAL_NUMBER_RE = re.compile(r'[0-9a-fA-F]+')

    @cached_property
    def serial_number(self):
        serial_number = self.dev.serial_number
        m = self._SERIAL_NUMBER_RE.search(serial_number)
        if m is None or (m.end() - m.start()) != 24:
            serial_number = ''.join(["%.2x" % ord(c) for c in list(serial_number)])
        return serial_number.upper()

    @cached_property
    def name(self):
        return f'ST-Link {self.type.version}'

    @cached_property
    def vendor_id(self):
        return self.dev.idVendor

    @cached_property
    def product_id(self):
        return self.dev.idProduct

    def __str__(self):
        return f"{self.name} (serial {self.serial_number})"


def get_stlink_devices() -> List[StLinkDevice]:
    """
    Get active stlink devices.
    """
    result = []
    for usb_dev in usb.core.find(find_all=True):
        stlink_device_type = _STLINK_DEVICE_TYPES.get((usb_dev.idVendor, usb_dev.idProduct))
        if stlink_device_type is None:
            continue
        result.append(StLinkDevice(dev=usb_dev, type=stlink_device_type))
    return result
