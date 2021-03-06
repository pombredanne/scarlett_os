#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_scarlett_os
----------------------------------

Tests for `scarlett_os` module.
"""


import sys
import unittest
import pytest
import click
import importlib
from contextlib import contextmanager
from click.testing import CliRunner

import scarlett_os
from scarlett_os.scripts.cli import main_group
from scarlett_os.tools import verify

import pprint

ubuntu_version = verify.get_current_os()
pp = pprint.PrettyPrinter(indent=4)


class TestScarlettCli(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_command_line_interface_help(self):
        runner = CliRunner()
        result = runner.invoke(main_group)
        assert result.exit_code == 0
        assert 'main_group' in result.output
        assert 'This is the command line interface to ScarlettOS' in result.output
        help_result = runner.invoke(main_group, ['--help'])
        assert help_result.exit_code == 0
        print(help_result.output)
        assert 'dbus_server|listener|tasker|check_all_services' in help_result.output


if __name__ == '__main__':
    sys.exit(unittest.main())
