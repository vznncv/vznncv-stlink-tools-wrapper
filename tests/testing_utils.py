import os
from collections import namedtuple
from contextlib import contextmanager
from os.path import join, dirname

FIXTURE_DIR = join(dirname(__file__), 'fixtures')

DeviceStub = namedtuple('NamedTuple', ['idVendor', 'idProduct', 'serial_number'])


@contextmanager
def change_dir(new_dir):
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)


def run_invoke_cmd(cli, args):
    try:
        cli.main(args=args)
    except SystemExit as e:
        return e.code
