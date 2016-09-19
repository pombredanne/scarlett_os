#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import platform
import re
import warnings

# Don't force people to install setuptools unless
# we have to.
try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

from setuptools import setup
from setuptools.command.test import test as TestCommand
from setuptools.command import install_lib

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    # TODO: put package requirements here
]

test_requirements = [
    'pytest'
]


# Pytest
class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['tests', '--ignore', 'tests/sandbox', '--verbose']
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name='scarlett_os',
    version='0.1.0',
    description="S.C.A.R.L.E.T.T is Tony Darks artificially programmed intelligent computer. She is programmed to speak with a female voice in a British accent.",
    long_description=readme + '\n\n' + history,
    author="Malcolm Jones",
    author_email='bossjones@theblacktonystark.com',
    url='https://github.com/bossjones/scarlett_os',
    packages=[
        'scarlett_os',
    ],
    package_dir={'scarlett_os':
                 'scarlett_os'},
    entry_points={
        'console_scripts': [
            'scarlett_os=scarlett_os.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='scarlett_os',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass={'test': PyTest},
    # cmdclass={"build_ext": custom_build_ext,
    #           "doc": doc,
    #           "test": test},
)
