import sys
import unittest

from django import __version__
from django.core.management import call_command
from django.test import SimpleTestCase, mock
from django.test.utils import captured_stdin, captured_stdout, patch_logger


class ShellCommandTestCase(SimpleTestCase):

    def test_command_option(self):
        with patch_logger('test', 'info') as logger:
            call_command(
                'shell',
                command=(
                    'import django; from logging import getLogger; '
                    'getLogger("test").info(django.__version__)'
                ),
            )
            self.assertEqual(len(logger), 1)
            self.assertEqual(logger[0], __version__)

    @unittest.skipIf(sys.platform == 'win32', "Windows select() doesn't support file descriptors.")
    @mock.patch('django.core.management.commands.shell.select')
    def test_stdin_read(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write('print(100)\n')
            stdin.seek(0)
            call_command('shell')
        self.assertEqual(stdout.getvalue().strip(), '100')
