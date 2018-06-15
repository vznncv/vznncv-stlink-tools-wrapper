# vznncv-stlink-tools

Helper wrapper around [OpenOCD](http://openocd.org/) to simplify
program uploading to microcontroller.

## Installation

The project requires python 3.6.

You can install the latest version from github:

```
pip install git+https://github.com/vznncv/vznncv-cubemx-tools
```

## Basic usage

If your stm project has the following structure:

```
...

build/<target>.elf

...

<openocd_config>.cfg

...
```
(you have one OpenOCD config *.cfg* file in the root and *.elf* file in the *build* directory)

You can type the following command from project root:

```
vznncv-stlink upload-app
```

No additional arguments require. The command automatically will find
*.cfg* and *.elf* files and upload program using OpenOCD.

If you don't set correctly version of the stlink interface in the
*.cfg* file, the command will try to determine it automatically
and upload program.

### Extra options

If you have multiple *.cfg* and *.elf* files or they have non-standard
location, you should specify them explicitly using `--elf-file` and
`--openocd-config` option. For example:

```
vznncv-stlink upload-app --openocd-config conf/stm.cfg --elf-file build/release/demo.cfg
```

If you work with multiple devices, you need a `--hla-serial` option to select
device for uploading. You can get information about available devices using command:

```
vznncv-stlink show-devices
```

Find target device and keep in mind its *hla-serial*. Upload program using
device *hla-serial*:

```
vznncv-stlink upload-app --hla-serial "\x21\x31\x35\x90\11"
```

If uploading fails you can get additional information using `-v` option:

```
vznncv-stlink upload-app -v
```