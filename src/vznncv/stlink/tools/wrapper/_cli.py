import logging
import os
from typing import Optional

import click

logger = logging.getLogger(__name__)

_CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
    'max_content_width': 120,
    'obj': {}
}


def _set_verbose(ctx, param, value):
    ctx.obj['verbose'] = value
    log_level = logging.DEBUG if value else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)-15s %(levelname)s: %(message)s')


def verbose_option(f):
    f = click.option('-v', '--verbose', help='Verbose output', is_flag=True,
                     callback=_set_verbose, is_eager=True, expose_value=False)(f)
    return f


@click.group(context_settings=_CONTEXT_SETTINGS)
def main():
    pass


_UPLOAD_BACKEND = ['pyocd', 'openocd', 'auto']


@main.command(name='upload-app', short_help='Upload compiled application')
@click.option('--project-dir', help='Project directory', type=click.Path(exists=True, file_okay=False),
              default=os.getcwd)
@click.option('--elf-file', help='Application elf file or folder with elf file')
@click.option('--backend', help='Backend to upload program', type=click.Choice(_UPLOAD_BACKEND), default='auto')
@click.option('--hla-serial', metavar='<hla-serial>',
              help='StLink device hla serial. It can be used to select concrete StLink '
                   'adapter if you have multiple ones')
@click.option('--openocd-path', help='OpenOCD path', type=click.Path(exists=True))
@click.option('--openocd-config', help='Explicit path to OpenOCD configuration. It it is not set, then script will try '
                                       'to find it automatically in the project directory',
              type=click.Path(exists=True))
@click.option('--pyocd-path', help='PyOCD path', type=click.Path(exists=True))
@click.option('--pyocd-target',
              help='PyOCD target. See `pyocd pack` and `pyocd list --targets` commands for more details')
@click.option('--pyocd-config', help='PyOCD config file. See `pyocd flash` commands for more details')
@click.option('--pyocd-script', help='PyOCD script file. See `pyocd flash` commands for more details')
@verbose_option
@click.pass_context
def upload_app(ctx, project_dir: str, elf_file: Optional[str], backend: str, hla_serial: Optional[str],
               openocd_path: Optional[str], openocd_config: Optional[str],
               pyocd_path: Optional[str], pyocd_target: Optional[str],
               pyocd_config: Optional[str], pyocd_script: Optional[str]):
    """
    Upload compiled application.


    """
    import vznncv.stlink.tools.wrapper._upload_utils as _upload_utils
    import traceback

    try:
        _upload_utils.upload_app(
            # common options
            project_dir=project_dir,
            elf_file=elf_file,
            backend=backend,
            hla_serial=hla_serial,
            verbose=ctx.obj['verbose'],
            # openocd options
            openocd_path=openocd_path,
            openocd_config=openocd_config,
            # pyocd options
            pyocd_path=pyocd_path,
            pyocd_target=pyocd_target,
            pyocd_config=pyocd_config,
            pyocd_script=pyocd_script
        )
    except Exception:
        logger.warning(traceback.format_exc())
        ctx.exit(1)


@main.command(name='show-devices', short_help='Show available stlink debugger/programmer')
@click.option('--format', help='Output format. "text" - human readable representation, "json" - json',
              type=click.Choice(['json', 'text']), default='text')
@verbose_option
def show_devices(format):
    """
    Show available ST-Link devices and information about them.

    The following infromation will be shown:

    - device name (ST-Link-V2, ST-Link-V2-1 or ST-Link-V3)
    - device vendor id
    - device product id
    - device hla number
    """
    from ._stlink_utils import get_stlink_devices
    import json

    device_infos = get_stlink_devices()
    if format == 'text':
        for device_info in device_infos:
            print(f'device: {device_info.name}')
            print(f'vendor id: 0x{device_info.vendor_id:04X}')
            print(f'product id: 0x{device_info.product_id:04X}')
            print(f'hla serial: {device_info.serial_number}')
            print("")
    elif format == 'json':
        output_dict = [dict(
            name=d.name,
            vendor_id=d.vendor_id,
            product_id=d.product_id,
            hla_serial=d.serial_number
        ) for d in device_infos]
        output_str = json.dumps(output_dict, indent=4)
        print(output_str)
    else:
        raise ValueError("Unknown format: {}".format(format))
