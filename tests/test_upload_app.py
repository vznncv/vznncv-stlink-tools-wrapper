from collections import namedtuple

from click.testing import CliRunner
from hamcrest import assert_that, equal_to, contains, greater_than
from os.path import join
from unittest.mock import patch

from testing_utils import BaseTestCase as TestCase, change_dir, FIXTURE_DIR
from vznncv.stlink.tools._cli import main
from vznncv.stlink.tools._devices_info import DeviceInfo


class OpenOCDCall(namedtuple('OpenOCDCall', ['args', 'retcode', 'stdout', 'stderr'])):
    __slots__ = []

    def __new__(cls, args=None, retcode=0, stdout='', stderr=''):
        return super().__new__(cls, args, retcode, stdout, stderr)


class UploadAppTestCase(TestCase):
    base_project_dir = join(FIXTURE_DIR, 'stm_project_stub')

    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

        # mock connected devices
        self.connected_stlink_devices = []

        def get_stlink_devices_stub():
            for stlink_device in self.connected_stlink_devices:
                if not isinstance(stlink_device, DeviceInfo):
                    raise ValueError('connected_stlink_devices contains non-DeviceInfo object. Please check test.')
            return self.connected_stlink_devices

        self.add_patch(patch('vznncv.stlink.tools._devices_info.get_stlink_devices', new=get_stlink_devices_stub))

        # mock openocd invocation
        self.openocd_call_mocks = []
        self.call_count = 0

        def call_openocd_mock(args):
            if self.call_count < len(self.openocd_call_mocks):
                expected_call = self.openocd_call_mocks[self.call_count]
            else:
                expected_call = None
            self.call_count += 1

            if not expected_call:
                raise ValueError("openocd shouldn't be invoked")

            if expected_call.args is not None:
                assert_that(args, contains(*expected_call.args))
            return expected_call.retcode, expected_call.stdout, expected_call.stderr

        self.add_patch(patch('vznncv.stlink.tools._upload_utils.call_openocd', call_openocd_mock))

    def invoke_command(self, args):
        with change_dir(self.project_dir):
            return self.runner.invoke(cli=main, args=args)

    def get_test_device_info_1(self):
        return [DeviceInfo(
            name='STMicroelectronics ST-LINK/V2.1',
            type='st-link v2.1',
            vendor_id=0x0483,
            product_id=0x374B,
            hla_serial='123',
            hla_serial_hex='\\x31\\x32\\x33',
            bus=1,
            address=1
        )]

    def test_auto_file_search_success(self):
        self.openocd_call_mocks.append(OpenOCDCall(args=[
            'openocd',
            '--file', self.get_abs_project_path('openocd_stm.cfg'),
            '--command', 'program "{}" verify reset exit'.format(self.get_abs_project_path('build/demo.elf'))
        ]))

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, equal_to(0), result.output)

    def test_auto_file_search_fail_1(self):
        self.create_project_file('build/demo_2.elf')

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(0))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_auto_file_search_fail_2(self):
        self.remove_project_file('build/demo.elf')

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(0))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_auto_file_search_fail_3(self):
        self.create_project_file('stm32f3.cfg')

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(0))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_implicit_file_specification_success(self):
        self.create_project_file('build/release/demo.elf')

        self.openocd_call_mocks.append(OpenOCDCall(args=[
            'openocd',
            '--file', self.get_abs_project_path('openocd_stm.cfg'),
            '--command', 'program "{}" verify reset exit'.format(self.get_abs_project_path('build/release/demo.elf'))
        ]))

        result = self.invoke_command([
            'upload-app',
            '--elf-file', 'build/release/demo.elf',
            '--openocd-config', 'openocd_stm.cfg'
        ])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, equal_to(0), result.output)

    def test_implicit_file_specification_fail(self):
        result = self.invoke_command([
            'upload-app',
            '--elf-file', 'build/release/demo.elf',
            '--openocd-config', 'openocd_stm.cfg'
        ])

        assert_that(self.call_count, equal_to(0))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_openocd_fail(self):
        self.openocd_call_mocks.append(OpenOCDCall(retcode=1))

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_hla_success(self):
        self.openocd_call_mocks.append(OpenOCDCall(args=[
            'openocd',
            '--file', self.get_abs_project_path('openocd_stm.cfg'),
            '--command', 'hla_serial "\\x31\\x32\\x33"',
            '--command', 'program "{}" verify reset exit'.format(self.get_abs_project_path('build/demo.elf'))
        ]))

        result = self.invoke_command(['upload-app', '--hla-serial', '\\x31\\x32\\x33'])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, equal_to(0), result.output)

    def test_interface_correction_fail(self):
        self.openocd_call_mocks.append(OpenOCDCall(retcode=1, stderr='*** OpenOCD init failed ***'))

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_interface_correction_hla_fail(self):
        self.openocd_call_mocks.append(OpenOCDCall(retcode=1, stderr='*** OpenOCD init failed ***'))
        self.connected_stlink_devices = self.get_test_device_info_1()

        result = self.invoke_command(['upload-app', '--hla-serial', '321'])

        assert_that(self.call_count, equal_to(1))
        assert_that(result.exit_code, greater_than(0), result.output)

    def test_openocd_interface_correction_success(self):
        self.openocd_call_mocks.append(OpenOCDCall(retcode=1, stderr='*** OpenOCD init failed ***'))
        self.openocd_call_mocks.append(OpenOCDCall(args=[
            'openocd',
            '--file', self.get_abs_project_path('openocd_stm.cfg'),
            '--file', 'interface/stlink-v2-1.cfg',
            '--command', 'program "{}" verify reset exit'.format(self.get_abs_project_path('build/demo.elf'))
        ]))
        self.connected_stlink_devices = self.get_test_device_info_1()

        result = self.invoke_command(['upload-app'])

        assert_that(self.call_count, equal_to(2))
        assert_that(result.exit_code, equal_to(0), result.output)

    def test_openocd_interface_correction_hla_success(self):
        self.openocd_call_mocks.append(OpenOCDCall(retcode=1, stderr='*** OpenOCD init failed ***'))
        self.openocd_call_mocks.append(OpenOCDCall(args=[
            'openocd',
            '--file', self.get_abs_project_path('openocd_stm.cfg'),
            '--file', 'interface/stlink-v2-1.cfg',
            '--command', 'hla_serial "\\x31\\x32\\x33"',
            '--command', 'program "{}" verify reset exit'.format(self.get_abs_project_path('build/demo.elf'))
        ]))
        self.connected_stlink_devices = self.get_test_device_info_1()

        result = self.invoke_command(['upload-app', '--hla-serial', '\\x31\\x32\\x33'])

        assert_that(self.call_count, equal_to(2))
        assert_that(result.exit_code, equal_to(0), result.output)
