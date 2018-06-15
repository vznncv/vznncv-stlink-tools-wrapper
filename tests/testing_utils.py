import os
import shutil
import tempfile
from contextlib import contextmanager
from os.path import isdir, basename, join, dirname, isfile, abspath
from unittest import TestCase


@contextmanager
def change_dir(new_dir):
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)


FIXTURE_DIR = join(dirname(__file__), 'fixtures')


class BaseTestCase(TestCase):
    base_project_dir = None

    def setUp(self):
        super().setUp()
        self.project_dir = None
        if self.base_project_dir is not None:
            project_name = basename(self.base_project_dir)
            self.project_dir = join(self.get_tmp_dir(), project_name)
            shutil.copytree(self.base_project_dir, self.project_dir)

    def get_tmp_dir(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        return tmp_dir

    def get_tmp_copy(self, fixture_dir):
        tmp_dir = self.get_tmp_dir()
        if not isdir(fixture_dir):
            raise ValueError("{} isn't directory".format(fixture_dir))
        fixture_name = basename(fixture_dir)
        tmp_fixture_dir = join(tmp_dir, fixture_name)
        shutil.copytree(fixture_dir, tmp_fixture_dir)
        return tmp_fixture_dir

    def add_patch(self, patch):
        if hasattr(patch, 'start'):
            patch.start()
            self.addCleanup(patch.stop)
        elif hasattr(patch, 'enable'):
            patch.enable()
            self.addCleanup(patch.disable)
        elif hasattr(patch, '__enter__'):
            patch.__enter__()
            self.addCleanup(patch.__exit__, None, None, None)
        else:
            raise ValueError("Unsupported patch: {}".format(patch))

    def create_project_file(self, rel_path):
        """
        Create stub project file
        """
        # ensure that folder exists
        file_path = join(self.project_dir, rel_path)
        file_dir = dirname(file_path)
        os.makedirs(file_dir, exist_ok=True)
        # create file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('// stub file\n')

    def remove_project_file(self, rel_path):
        """
        Remove project file/directory
        """
        file_path = join(self.project_dir, rel_path)
        if isfile(file_path):
            os.remove(file_path)
        elif isdir(file_path):
            shutil.rmtree(file_path)
        else:
            raise ValueError("File '{}' doesn't exist".format(file_path))

    def get_abs_project_path(self, rel_path):
        """
        Get absolute path of the project file
        """
        return abspath(join(self.project_dir, rel_path))
