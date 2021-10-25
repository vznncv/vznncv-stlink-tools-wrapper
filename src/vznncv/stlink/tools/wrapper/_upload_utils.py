import itertools
import logging
import os.path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Optional, Tuple

from cached_property import cached_property

from ._search_utils import resolve_elf_file_location, resolve_openocd_config_file
from ._stlink_utils import get_stlink_devices, StLinkDevice

logger = logging.getLogger(__name__)


def _list_device_info(stlink_devices):
    return [f'- {stlink_device.name}; hla serial {stlink_device.serial_number}' for stlink_device in stlink_devices]


def upload_app(project_dir: str, elf_file: Optional[str], backend: str, hla_serial: Optional[str], *,
               openocd_config: Optional[str], openocd_path: Optional[str],
               pyocd_path: Optional[str], pyocd_target: Optional[str],
               pyocd_config: Optional[str], pyocd_script: Optional[str],
               verbose: bool = False):
    """
    Upload compiled .elf firmware to target board.
    """
    # resolve elf file location
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        raise ValueError(f"Project directory \"{project_dir}\" doesn't not exist")
    elf_file = resolve_elf_file_location(project_dir=project_dir, elf_path=elf_file)
    logger.info(f"Target elf file to upload: {elf_file}")

    # resolve stlink device
    stlink_devices = get_stlink_devices()
    if not stlink_devices:
        raise ValueError("Cannot find any ST-Link device")
    elif hla_serial is not None:
        target_devices = [
            stlink_device for stlink_device in stlink_devices if
            stlink_device.serial_number.upper() == hla_serial.upper()
        ]
        if not target_devices:
            raise ValueError("Cannot find stink device with hla serial: {}\n"
                             "Available devices:\n{}".format(hla_serial, '\n'.join(_list_device_info(stlink_devices))))
        elif len(target_devices) > 1:
            raise ValueError("Found multiple stink devices with the same serial:{}\n".format(
                '\n'.join(_list_device_info(stlink_devices))
            ))
        target_device = target_devices[0]
    elif len(stlink_devices) == 1:
        target_device = stlink_devices[0]
    else:
        raise ValueError("Found multiple stink devices:\n{}\nPlease specify one with hal serial number".format(
            '\n'.join(_list_device_info(stlink_devices))
        ))
    logger.info(f"Target ST-Link device: {target_device}")

    # check pyocd/openocd paths
    if pyocd_path is None:
        pyocd_path = shutil.which('pyocd')
    elif not os.path.isfile(pyocd_path):
        raise ValueError(f'Give pyocd path "{pyocd_path}" does not exists')
    if openocd_path is None:
        openocd_path = shutil.which('openocd')
    elif not os.path.isfile(openocd_path):
        raise ValueError(f'Give openocd path "{openocd_path}" does not exists')

    # resolve backend
    if backend == 'auto':
        if pyocd_path is None and openocd_path is not None:
            backend = 'openocd'
        elif pyocd_path is not None and openocd_path is None:
            backend = 'pyocd'
        elif pyocd_path is None and openocd_path is None:
            raise ValueError("Cannot choose backend, as pyocd and openocd aren't found in the PATH"
                             " or specified explicitly")
        else:
            if openocd_config is not None:
                backend = 'openocd'
            elif pyocd_target is not None:
                backend = 'pyocd'
            else:
                backend = 'openocd'
        logger.info(f"Select \"{backend}\" for program uploading automatically")
    logger.info(f"Upload backend: \"{backend}\"")

    # upload application
    if backend == 'openocd':
        _upload_app_with_openocd(
            project_dir=project_dir,
            elf_file=elf_file,
            stlink_device=target_device,
            verbose=verbose,
            openocd_path=openocd_path,
            openocd_config=openocd_config
        )
    elif backend == 'pyocd':
        _upload_app_with_pyocd(
            project_dir=project_dir,
            elf_file=elf_file,
            stlink_device=target_device,
            verbose=verbose,
            pyocd_path=pyocd_path,
            pyocd_target=pyocd_target,
            pyocd_config=pyocd_config,
            pyocd_script=pyocd_script,
        )
    logger.info("Complete")


def _shlex_join(args):
    return ' '.join(shlex.quote(arg) for arg in args)


def _grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


class _OpenOCDCompat:
    """
    Helper wrapper for compatibility with different openocd versions.
    """

    def __init__(self, openocd_path):
        self._openocd_path = openocd_path

    _VERSION_RE = re.compile(r'\bv?(?P<version>\d+\.\d+\.+\d+)\b')

    @cached_property
    def openocd_version(self) -> Tuple[int, ...]:
        try:
            openocd_version_info = subprocess.check_output(
                [self._openocd_path, '--version'],
                encoding='utf-8', stderr=subprocess.STDOUT
            )
        except Exception as e:
            raise ValueError("Fail to resolve openocd version") from e
        m = self._VERSION_RE.search(openocd_version_info)
        if m is None:
            raise ValueError(f"Fail to resolve openocd version. Cannot parse openocd output:\n\n{openocd_version_info}")
        return tuple(int(item) for item in m.group('version').split('.'))

    def get_openocd_hla_serial(self, stlink_device: StLinkDevice) -> str:
        if len(stlink_device.serial_number) != 24:
            raise ValueError(f"Invalid serial number length: {stlink_device.serial_number}")

        if self.openocd_version < (0, 11):
            # openocd 0.10 and lower
            openocd_hla_serial_codes = []
            # convert hla_serial to openocd format
            for g in _grouper(stlink_device.serial_number, 2):
                serial_code = int(f'{g[0]}{g[1]}', 16)
                # openocd hla bug workaround: replace all non-ascii symbols by ? (0x3F)
                if serial_code > 0x7F:
                    serial_code = 0x3F
                openocd_hla_serial_codes.append(serial_code)
            openocd_hla_serial = ''.join(f'\\x{serial_code:02X}' for serial_code in openocd_hla_serial_codes)
        else:
            # openocd 0.11 and higher
            openocd_hla_serial = stlink_device.serial_number

        return openocd_hla_serial


def _upload_app_with_openocd(*, project_dir: str, elf_file: str, stlink_device: StLinkDevice, verbose: bool,
                             openocd_path: str,
                             openocd_config: Optional[str]):
    # resolve openocd configuration
    openocd_config = resolve_openocd_config_file(project_dir=project_dir, config_path=openocd_config)
    openocd_compat = _OpenOCDCompat(openocd_path)
    logger.info(f"OpenOCD configuration file: {openocd_config}")

    # prepare OpenOCD command
    command_args = [openocd_path]
    if verbose:
        command_args.extend(['--debug'])
    command_args.extend(['--file', openocd_config])

    openocd_hla_serial = openocd_compat.get_openocd_hla_serial(stlink_device)
    command_args.extend(['--command', f'hla_serial "{openocd_hla_serial}"'])
    command_args.extend(['--command', f'program "{elf_file}" verify reset exit'])

    logger.info(f"Run command: {_shlex_join(command_args)}")
    logger.info("============================= start of openocd logs ============================")
    result = subprocess.run(command_args, stdout=sys.stderr, cwd=project_dir)
    logger.info("============================== end of openocd logs =============================")
    logger.info(f"OpenOCD return code: {result.returncode}")
    if result.returncode != 0:
        raise ValueError(f"OpenOCD has failed with code {result.returncode}")


def _upload_app_with_pyocd(*, project_dir: str, elf_file: str, stlink_device: StLinkDevice, verbose: bool,
                           pyocd_path: str,
                           pyocd_target: Optional[str], pyocd_config: Optional[str], pyocd_script: Optional[str]):
    # resolve pyocd target
    if pyocd_target is None:
        raise ValueError("PyOCD target isn't specified. Please specify '--pyocd-target' option to use pyocd backend")

    # prepare PyOCD command
    command_args = [pyocd_path, 'flash']
    if verbose:
        command_args.append('--verbose')
    command_args.append('--trust-crc')
    command_args.extend(['--target', pyocd_target])
    command_args.extend(['--uid', stlink_device.serial_number])
    if pyocd_config is not None:
        command_args.extend(['--config', pyocd_config])
    if pyocd_script is not None:
        command_args.extend(['--script', pyocd_script])
    command_args.extend(['--format', 'elf'])
    command_args.append(elf_file)

    logger.info(f"Run command: {_shlex_join(command_args)}")
    logger.info("============================== start of pyocd logs =============================")
    result = subprocess.run(command_args, stdout=sys.stderr, cwd=project_dir)
    logger.info("=============================== end of pyocd logs ==============================")
    logger.info(f"PyOCD return code: {result.returncode}")
    if result.returncode != 0:
        raise ValueError(f"PyOCD has failed with code {result.returncode}")
