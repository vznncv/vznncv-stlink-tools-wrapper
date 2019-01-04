import logging

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
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')


def verbose_option(f):
    f = click.option('-v', '--verbose', help='Verbose output', is_flag=True,
                     callback=_set_verbose, is_eager=True, expose_value=False)(f)
    return f


@click.group(context_settings=_CONTEXT_SETTINGS)
def main():
    pass


@main.command(name='upload-app', short_help='Upload compiled application using OpenOCD')
@click.option('--elf-file', metavar='<elf-file>', help='Application elf file or folder with elf file',
              type=click.Path(exists=True))
@click.option('--openocd-config', metavar='<openocd-config>', help='OpenOCD microcontroller configuration file',
              type=click.Path(exists=True))
@click.option('--project-dir', metavar='<project-dir>', help='Project directory',
              type=click.Path(exists=True, file_okay=False))
@click.option('--openocd-path', metavar='<openocd-path>', help='OpenOCD path', type=click.Path(exists=True))
@click.option('--hla-serial', metavar='<hla-serial>', help='stlink device hla serial')
@verbose_option
@click.pass_context
def upload_app(ctx, elf_file, openocd_config, project_dir, openocd_path, hla_serial):
    """
    Upload compiled application using OpenOCD.

    To simplify command usage and IDE integration it allows not strict specification
    of the application "elf" file and openocd configuration location.

    The "elf" file is searched in the following order:

    \b
    - if <elf-file> is set and it's file, then it's used
    - if <elf-file> is set and it's folder, then "elf" file is searched in this folder
    - if <project-dir> is set, then "elf" file is searched in the "<project-dir>/build" directory
    - "elf" file is searched in the  "<current-directory>/build" directory

    The "elf" searching finishes successfully, if folder contains only one file with "elf" extension,
    otherwise an error will be shown.

    The openocd configuration is search in the following order:

    \b
    - if <openocd-config> is set and it's file, then it's used
    - if <openocd-config> isn't set and it's folder, then it's searched in the <openocd-config> folder
    - openocd config file is searched in the current directory

    The openocd config searching finishes successfully, if folder contains only one file with "cfg" extension,
    otherwise an error will be shown.

    If specified <openocd-config> doesn't work, then it's command try to adjust interface configuration,
    if it's possibly.

    If you want to use openocd not from the PATH variable, you can specify it explicitly using "--openocd-path" option.

    In case when you use multiple stlink adapters, you should specify <hla-serial> to use correct stlink device.
    """
    import vznncv.stlink.tools._upload_utils as _upload_utils
    import os
    import traceback

    if project_dir is None:
        project_dir = os.getcwd()

    try:
        _upload_utils.upload_app(
            elf_file=elf_file,
            openocd_config=openocd_config,
            project_dir=project_dir,
            openocd_path=openocd_path,
            hla_serial=hla_serial,
            verbose=ctx.obj['verbose']
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
    Show available stlink devices and information about them.

    The following infromation will be shown:

    - device name
    - device type (stlink-v2 or stlink-v2.1)
    - device vendor id
    - device product id
    - device hla number
    - device hla number (hexidemical form)
    - device bus no
    - device address
    """
    import vznncv.stlink.tools._devices_info as _devices_info
    import json
    from collections import OrderedDict

    device_infos = _devices_info.get_stlink_devices()
    if format == 'text':
        for device_info in device_infos:
            print('\n{:=<80}'.format(device_info.name + ' '))
            print('vendor id: 0x{:04X}'.format(device_info.vendor_id))
            print('product id: 0x{:04X}'.format(device_info.product_id))
            print('hla serial: {}'.format(device_info.hla_serial))
            print('hla serial (hex): {}'.format(device_info.hla_serial_hex))

    elif format == 'json':
        output_dict = [OrderedDict(
            name=d.name,
            type=d.type,
            vendor_id=d.vendor_id,
            product_id=d.product_id,
            hla_serial=d.hla_serial,
            hla_serial_hex=d.hla_serial_hex,
            bus=d.bus,
            address=d.address
        ) for d in device_infos]
        output_str = json.dumps(output_dict, indent=4)
        print(output_str)
    else:
        raise ValueError("Unknown format: {}".format(format))


if __name__ == '__main__':
    main()
