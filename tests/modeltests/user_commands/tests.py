from StringIO import StringIO

from django.test import TestCase
from django.core import management
from django.core.management.base import CommandError

class CommandTests(TestCase):
    def test_command(self):
        out = StringIO()
        management.call_command('dance', stdout=out)
        self.assertEquals(out.getvalue(),
            "I don't feel like dancing Rock'n'Roll.")

    def test_command_style(self):
        out = StringIO()
        management.call_command('dance', style='Jive', stdout=out)
        self.assertEquals(out.getvalue(),
            "I don't feel like dancing Jive.")

    def test_explode(self):
        self.assertRaises(CommandError, management.call_command, ('explode',))