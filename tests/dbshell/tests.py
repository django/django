from unittest import mock

from mango.core.management import call_command
from mango.core.management.base import CommandError
from mango.db import connection
from mango.test import SimpleTestCase


class DbshellCommandTestCase(SimpleTestCase):
    def test_command_missing(self):
        msg = (
            'You appear not to have the %r program installed or on your path.'
            % connection.client.executable_name
        )
        with self.assertRaisesMessage(CommandError, msg):
            with mock.patch('subprocess.run', side_effect=FileNotFoundError):
                call_command('dbshell')
