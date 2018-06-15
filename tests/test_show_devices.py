import json
from click.testing import CliRunner
from hamcrest import assert_that, equal_to, string_contains_in_order
from unittest.mock import patch

from testing_utils import BaseTestCase as TestCase
from vznncv.stlink.tools._cli import main
from vznncv.stlink.tools._devices_info import DeviceInfo


class ShowDevicesTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

        self.connected_stlink_devices = []

        def get_stlink_devices_stub():
            for stlink_device in self.connected_stlink_devices:
                if not isinstance(stlink_device, DeviceInfo):
                    raise ValueError('connected_stlink_devices contains non-DeviceInfo object. Please check test.')
            return self.connected_stlink_devices

        self.add_patch(patch('vznncv.stlink.tools._devices_info.get_stlink_devices', new=get_stlink_devices_stub))

    def test_show_nothing_human(self):
        self.connected_stlink_devices = []
        result = self.runner.invoke(main, ['show-devices'])

        assert_that(result.exit_code, equal_to(0))
        assert_that(result.output.strip(), equal_to(''))

    def test_show_nothing_json(self):
        self.connected_stlink_devices = []
        result = self.runner.invoke(main, ['show-devices', '--format', 'json'])

        assert_that(result.exit_code, equal_to(0))
        data = json.loads(result.output)
        assert_that(data, equal_to([]))

    def get_test_device_info(self):
        return [DeviceInfo(
            name='STMicroelectronics ST-LINK/V2.1',
            type='st-link v2.1',
            vendor_id=0x0483,
            product_id=0x374B,
            hla_serial='123',
            hla_serial_hex='\\x31\\x32\\x33',
            bus=1,
            address=1
        ), DeviceInfo(
            name='STMicroelectronics ST-LINK/V2',
            type='st-link v2',
            vendor_id=0x0483,
            product_id=0x3748,
            hla_serial='121',
            hla_serial_hex='\\x31\\x32\\x31',
            bus=1,
            address=1
        ), ]

    def test_show_devices_human(self):
        self.connected_stlink_devices = self.get_test_device_info()
        result = self.runner.invoke(main, ['show-devices'])

        lines_to_match = []
        for stlink_device in self.connected_stlink_devices:
            lines_to_match.append(stlink_device.name)
            lines_to_match.extend(['vendor id', '0x{:04X}'.format(stlink_device.vendor_id)])
            lines_to_match.extend(['product id', '0x{:04X}'.format(stlink_device.product_id)])
            lines_to_match.extend(['hla serial', stlink_device.hla_serial])
            lines_to_match.extend(['hla serial (hex)', stlink_device.hla_serial_hex])

        assert_that(result.exit_code, equal_to(0))
        assert_that(result.output, string_contains_in_order(*lines_to_match))

    def test_show_devices_json(self):
        self.connected_stlink_devices = self.get_test_device_info()
        result = self.runner.invoke(main, ['show-devices', '--format', 'json'])

        expected_data = [dict(zip(stlink_device._fields, stlink_device)) for stlink_device in
                         self.connected_stlink_devices]

        assert_that(result.exit_code, equal_to(0))
        data = json.loads(result.output)
        assert_that(data, equal_to(expected_data))
