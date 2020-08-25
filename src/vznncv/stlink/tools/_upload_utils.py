import enum
import logging
import re
import subprocess
import time
from os.path import join

import vznncv.stlink.tools._devices_info as _devices_info

from ._search_utils import resolve_filepath, FileNotFound, MultipleFilesAreFound
from ._utils import format_command

logger = logging.getLogger(__name__)


# def _find_file_in_dir(dir_path, extension):
#     target = None
#     logger.info("Try to find '{}' file in the folder '{}'".format(extension, dir_path))
#     filenames = [filename for filename in os.listdir(dir_path) if splitext(filename)[1].lower() == extension]
#     if not filenames:
#         logger.info("Cannot find files with extension '{}'".format(extension))
#     elif len(filenames) == 1:
#         target = join(dir_path, filenames[0])
#     else:
#         logger.info("Multiple files with extension '{}' are found: {}. But we need only one file"
#                     .format(extension, ', '.join(filenames)))
#
#     if target is not None:
#         logger.info("Found '{}'".format(target))
#     return target
#
#
# def _find_file(file_path=None, alternative_dir=None, extension=None):
#     if file_path is not None:
#         if isfile(file_path):
#             target = abspath(file_path)
#         else:
#             target = _find_file_in_dir(file_path, extension)
#     else:
#         target = _find_file_in_dir(alternative_dir, extension)
#
#     return target


def call_openocd(args):
    """
    Helper function to call openocd.

    It's move to separate function to facilitate its mocking for testing.
    :param args:
    :return: <retcode>, <stdout>, <stderr>
    """
    result = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
    return result.returncode, result.stdout, result.stderr


def _parse_openocd_logs(log_text):
    parsed_logs = []
    log_level = logging.INFO
    start_pos = 0

    for m in re.finditer(r'^(?P<level_name>\w{,8})\s{,6}:', log_text, re.MULTILINE):
        prev_logs = log_text[start_pos:m.start()].strip()
        if prev_logs:
            parsed_logs.append((log_level, prev_logs))
        start_pos = m.end()

        level_name = m.group('level_name').lower()
        if level_name == 'error':
            log_level = logging.ERROR
        elif level_name.startswith('warn'):
            log_level = logging.WARNING
        elif log_level == logging.DEBUG:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

    prev_logs = log_text[start_pos:].strip()
    if prev_logs:
        parsed_logs.append((log_level, prev_logs))

    return parsed_logs


class _OCDCallResult(enum.Enum):
    SUCCESS = 0
    INIT_ERROR = 1


def _call_openocd_and_check_results(configs, commands, verbose=False, openocd_path=None):
    # prepare command
    command_args = []
    command_args.append(configs if openocd_path is not None else 'openocd')
    if verbose:
        command_args.extend(['--debug', '3'])
    for config_file in configs:
        command_args.extend(['--file', config_file])
    for command in commands:
        command_args.extend(['--command', command])

    logger.info("Run: {}".format(format_command(command_args)))
    cmd_start = time.time()
    ret_code, stdout, stderr = call_openocd(command_args)
    cmd_time = time.time() - cmd_start
    logger.info("Command execution time: {:.2f} seconds".format(cmd_time))
    logger.info("================ openocd logs ================")
    for log_level, message in _parse_openocd_logs(stderr):
        logger.log(log_level, message)
    if stdout.strip():
        logger.info(stdout)
    logger.info("============= end of openocd logs =============")
    if ret_code != 0:
        logger.error("OpenOCD failed. Return code: {}".format(ret_code))

    # check init error
    if re.search(r'init failed', stderr, re.MULTILINE | re.IGNORECASE):
        return _OCDCallResult.INIT_ERROR
    elif ret_code == 0:
        return _OCDCallResult.SUCCESS
    else:
        raise subprocess.CalledProcessError(
            returncode=ret_code,
            cmd=command_args[0],
            output=stdout,
            stderr=stderr
        )


def _detect_interface(hla_serial=None):
    devices = _devices_info.get_stlink_devices()
    if hla_serial is not None:
        hla_serial = hla_serial.encode('utf-8').decode('unicode_escape')
        devices = list(filter(lambda d: d.hla_serial == hla_serial, devices))

    if not devices:
        logger.warning('Cannot detect any device')
        return None

    if len(devices) > 1:
        logger.warning("Found multiple devices, select the first ...")
    device = devices[0]
    if device.type == 'st-link v2':
        interface_file = 'interface/stlink-v2.cfg'
    elif device.type == 'st-link v2.1':
        interface_file = 'interface/stlink-v2-1.cfg'
    else:
        raise ValueError("Unknown device type: {}".format(device.type))
    logger.info("The '{}' is detected".format(device.type))

    return interface_file


def upload_app(*, elf_file, openocd_config, project_dir, openocd_path=None, hla_serial=None, verbose=False):
    logger.info("Determine *.elf file location")
    elf_file = resolve_filepath(
        explicit_filepath=elf_file,
        alternative_dirs=[join(project_dir, 'build'), join(project_dir, 'BUILD')],
        extension='.elf',
        max_depth=2
    )

    try:
        cfg_file = resolve_filepath(
            explicit_filepath=openocd_config,
            alternative_dirs=[project_dir],
            extension='.cfg',
            exclude_patterns=['TESTS', 'mbed-os']
        )
    except FileNotFound as e:
        raise ValueError(f"Cannot find openocd files. "
                         f"Please put *.cgf for your mcu to project directory \"{project_dir}\"") from e
    except MultipleFilesAreFound as e:
        raise ValueError(f"Found multiple openocd files in the project directory \"{project_dir}\". "
                         f"Please leave only one openocd file or specify it explicitly") from e

    # prepare openocd command arguments
    config_args = [cfg_file]
    command_args = []
    if hla_serial is not None:
        command_args.append('hla_serial "{}"'.format(hla_serial))
    command_args.append('program "{}" verify reset exit'.format(elf_file))

    # try to upload program
    res = _call_openocd_and_check_results(
        configs=config_args,
        commands=command_args,
        verbose=verbose,
        openocd_path=openocd_path
    )
    if res == _OCDCallResult.SUCCESS:
        logger.info("Program has been uploaded successfully")
        return
    elif res != _OCDCallResult.INIT_ERROR:
        raise ValueError("Unknown res value: {}".format(res))

    # try to adjust configuration
    logger.warning("Fail to upload program. Try to autodetect interface")
    interface_file = _detect_interface(hla_serial)
    if interface_file is None:
        raise ValueError("Cannot upload program. See logs")
    config_args.append(interface_file)
    res = _call_openocd_and_check_results(
        configs=config_args,
        commands=command_args,
        verbose=verbose,
        openocd_path=openocd_path
    )
    if res == _OCDCallResult.SUCCESS:
        logger.info("Program has been uploaded successfully")
    else:
        raise ValueError("Cannot upload program. See logs")
