#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from setuptools import setup, find_packages

project_name = 'vznncv-stlink-tools'

with open('README.md') as readme_file:
    readme = readme_file.read()
readme = re.sub(r'!\[[^\[\]]*\]\S*', '', readme)

_locals = {}
with open('src/' + project_name.replace('-', '/') + '/_version.py') as fp:
    exec(fp.read(), None, _locals)
__version__ = _locals['__version__']

with open('requirements_dev.txt') as fp:
    test_requirements = fp.read()

setup(
    author="Konstantin Kochin",
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
    description="CMake project generator from STM32CubeMX project",
    long_description=readme,
    long_description_content_type="text/markdown",
    license='MIT',
    include_package_data=True,
    name=project_name,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'vznncv-stlink = vznncv.stlink.tools._cli:main',
        ]
    },
    install_requires=[
        'click',
        'pyusb'
    ],
    tests_require=test_requirements,
    version=__version__
)
