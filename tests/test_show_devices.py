import json
from collections import namedtuple
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from hamcrest import assert_that, string_contains_in_order, contains_inanyorder

from vznncv.stlink.tools.wrapper._cli import main
from testing_utils import DeviceStub


@pytest.fixture
def no_usb_devices():
    with patch('usb.core.find', autospec=True) as find_mock:
        find_mock.return_value = []
        yield


def test_no_usb_devices_text(no_usb_devices):
    cli_runner = CliRunner(mix_stderr=False)
    result = cli_runner.invoke(main, ['show-devices'])
    assert result.exit_code == 0
    assert result.stdout.strip() == ''


def test_no_usb_devices_json(no_usb_devices):
    cli_runner = CliRunner(mix_stderr=False)
    result = cli_runner.invoke(main, ['show-devices', '--format', 'json'])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == []


@pytest.fixture
def dummy_usb_devices():
    with patch('usb.core.find', autospec=True) as find_mock:
        find_mock.return_value = [
            DeviceStub(idVendor=0x0BDA, idProduct=0x0411, serial_number=None),
            # '34006a063141323910300243'
            DeviceStub(idVendor=0x0483, idProduct=0x3748, serial_number=b'4\x00j\x061A29\x100\x02C'.decode('utf-8')),
            DeviceStub(idVendor=0x0483, idProduct=0x374e, serial_number='002F003D3438510B34313939')
        ]
        yield


def test_usb_devices_text(dummy_usb_devices):
    cli_runner = CliRunner(mix_stderr=False)
    result = cli_runner.invoke(main, ['show-devices'])
    assert result.exit_code == 0
    assert_that(result.stdout, string_contains_in_order(
        'ST-Link V2', '0x0483', '0x3748', '34006A063141323910300243',
        'ST-Link V3E', '0x0483', '0x374E', '002F003D3438510B34313939'
    ))


def test_usb_devices_json(dummy_usb_devices):
    cli_runner = CliRunner(mix_stderr=False)
    result = cli_runner.invoke(main, ['show-devices', '--format', 'json'])
    assert result.exit_code == 0
    assert_that(json.loads(result.stdout), contains_inanyorder(
        {'name': 'ST-Link V2', 'vendor_id': 1155, 'product_id': 14152, 'hla_serial': '34006A063141323910300243'},
        {'name': 'ST-Link V3E', 'vendor_id': 1155, 'product_id': 14158, 'hla_serial': '002F003D3438510B34313939'}
    ))
