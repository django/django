import sys
import unittest

from django import __version__
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, mock
from django.test.utils import captured_stdin, captured_stdout, patch_logger

try:
    import IPython
except:
    IPython = None

try:
    import bpython
except:
    bpython = None


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

    # If we don't patch select then the following tests will fail when the test
    # suite is run in parallel mode.  This is because the the tests are run in
    # a subprocess and the subprocess's stdin is closed and replaced by
    # /dev/null.  Reading from /dev/null always returns EOF and so select will
    # always show that sys.stdin is ready to read.  This causes problems
    # because of the call to select.select towards the end of
    # django.core.management.commands.shell.BaseCommand.handle.

    @unittest.skipIf(IPython is not None, 'IPython is installed')
    @mock.patch('django.core.management.commands.shell.select.select')
    def test_shell_with_ipython_not_installed(self, select):
        select.return_value = [[], [], []]
        with self.assertRaisesMessage(CommandError, "Couldn't import ipython interface."):
            call_command('shell', interface='ipython')

    @unittest.skipIf(bpython is not None, 'bython is installed')
    @mock.patch('django.core.management.commands.shell.select.select')
    def test_shell_with_bpython_not_installed(self, select):
        select.return_value = [[], [], []]
        with self.assertRaisesMessage(CommandError, "Couldn't import bpython interface."):
            call_command('shell', interface='bpython')
