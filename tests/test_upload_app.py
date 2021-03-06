import os
import os.path
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from hamcrest import assert_that, string_contains_in_order

from testing_utils import DeviceStub, FIXTURE_DIR, change_dir, run_invoke_cmd
from vznncv.stlink.tools.wrapper._cli import main


@pytest.fixture
def dummy_usb_devices():
    with patch('usb.core.find', autospec=True) as find_mock:
        find_mock.return_value = [
            DeviceStub(idVendor=0x0BDA, idProduct=0x0411, serial_number=None),
            DeviceStub(idVendor=0x0483, idProduct=0x374e, serial_number='002F003D3438510B34313939')
        ]
        yield


@pytest.fixture
def demo_project_path(tmp_path: Path):
    project_dir = tmp_path / 'stm_project'
    shutil.copytree(os.path.join(FIXTURE_DIR, 'stm_project_stub'), project_dir)
    yield project_dir


@pytest.fixture
def tmp_bin_dir(tmp_path: Path):
    tmp_bin = tmp_path / 'bin'
    os.makedirs(tmp_bin, exist_ok=True)

    original_environ = os.environ.copy()
    path_var = f"{tmp_bin}{os.pathsep}{os.environ.get('PATH', '')}"
    try:
        os.environ['PATH'] = path_var
        yield tmp_bin
    finally:
        os.environ.clear()
        os.environ.update(original_environ)


@pytest.fixture
def openocd_stub_path(tmp_bin_dir):
    openocd_path = tmp_bin_dir.joinpath('openocd')
    openocd_path.write_text(r'''
#!/bin/sh
echo "OpenOCD stub" 1>&2
echo "OpenOCD args: $@" 1>&2
'''.lstrip())
    openocd_path.chmod(0o777)
    yield openocd_path


@pytest.fixture
def pyocd_stub_path(tmp_bin_dir):
    openocd_path = tmp_bin_dir.joinpath('pyocd')
    openocd_path.write_text(r'''
#!/bin/sh
echo "PyOCD stub" 1>&2
echo "PyOCD args: $@" 1>&2
'''.lstrip())
    openocd_path.chmod(0o777)
    yield openocd_path


def test_openocd_usage(demo_project_path: Path, openocd_stub_path: Path, dummy_usb_devices, capfd):
    with change_dir(demo_project_path):
        exit_code = run_invoke_cmd(main, ['upload-app', '--backend', 'openocd', '--elf-file', 'build'])

    assert exit_code == 0
    out_result = capfd.readouterr()
    assert_that(out_result.err, string_contains_in_order(
        'Target elf file ', 'build/demo.elf',
        'Target ST-Link device: ST-Link V3E',
        'Upload backend: "openocd"',
        'Run command', 'openocd', '--file', 'openocd_stm.cfg', '--command', 'program', 'demo.elf', 'verify reset exit',
        'OpenOCD stub',
        'OpenOCD args', '--file', 'openocd_stm.cfg', '--command', 'program', 'demo.elf', 'verify reset exit',
        'Complete',
    ))


def test_pyocd_usage(demo_project_path: Path, pyocd_stub_path: Path, dummy_usb_devices, capfd):
    with change_dir(demo_project_path):
        exit_code = run_invoke_cmd(main, ['upload-app', '--backend', 'pyocd', '--elf-file', 'build', '--pyocd-target',
                                          'stm32f411ce'])

    assert exit_code == 0
    out_result = capfd.readouterr()
    assert_that(out_result.err, string_contains_in_order(
        'Target elf file ', 'build/demo.elf',
        'Target ST-Link device: ST-Link V3E',
        'Upload backend: "pyocd"',
        'Run command', 'pyocd', 'flash', '--target', 'stm32f411ce', '--format', 'elf', 'demo.elf',
        'PyOCD stub',
        'PyOCD args', 'flash', '--target', 'stm32f411ce', '--format', 'elf', 'demo.elf',
        'Complete',
    ))
