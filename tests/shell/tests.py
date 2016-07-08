from django import __version__
from django.core.management import call_command
from django.test import SimpleTestCase
from django.test.utils import patch_logger


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
