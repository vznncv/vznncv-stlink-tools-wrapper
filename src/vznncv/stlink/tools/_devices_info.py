from collections import namedtuple

import usb.core

_DeviceIdInfo = namedtuple('DeviceIdInfo', ['type', 'name', 'vendor_id', 'product_id'])
_STLINK_DEVICES = {(d.vendor_id, d.product_id): d for d in [
    _DeviceIdInfo('st-link v2', 'STMicroelectronics ST-LINK/V2', 0x0483, 0x3748),
    _DeviceIdInfo('st-link v2.1', 'STMicroelectronics ST-LINK/V2.1', 0x0483, 0x374B),
]}

DeviceInfo = namedtuple('DeviceInfo', ['name', 'type', 'vendor_id', 'product_id',
                                       'hla_serial', 'hla_serial_hex', 'bus', 'address'])


def get_stlink_devices():
    stlink_devices = list(usb.core.find(
        custom_match=lambda d: (d.idVendor, d.idProduct) in _STLINK_DEVICES,
        find_all=True
    ))

    device_infos = []

    for stlink_device in stlink_devices:
        device_id_info = _STLINK_DEVICES[(stlink_device.idVendor, stlink_device.idProduct)]
        device_infos.append(DeviceInfo(
            name=device_id_info.name,
            type=device_id_info.type,
            vendor_id=device_id_info.vendor_id,
            product_id=device_id_info.product_id,
            hla_serial=stlink_device.serial_number,
            hla_serial_hex=''.join(r'\x{:02x}'.format(ord(c)) for c in stlink_device.serial_number),
            bus=stlink_device.bus,
            address=stlink_device.address
        ))

    return device_infos
