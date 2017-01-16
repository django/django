from django.core.management import call_command, signals
from django.test import SimpleTestCase, mock
from django.utils.six import StringIO


class ManagementSignalsTestCase(SimpleTestCase):

    def setUp(self):
        from django.core.management.commands.runserver import Command

        def monkey_run(*args, **options):
            return

        self.output = StringIO()
        self.cmd = Command(stdout=self.output)
        self.cmd.run = monkey_run

    def test_pre_command_signal(self):
        handler = mock.Mock()
        signals.pre_command.connect(handler, sender=self.cmd.__class__)
        call_command(self.cmd, verbosity=0, interactive=False)
        handler.assert_called_once()
        args, kwargs = handler.call_args
        self.assertEqual(kwargs['instance'], self.cmd)
        self.assertEqual(kwargs['sender'], self.cmd.__class__)

    def test_post_command_signal(self):
        handler = mock.Mock()
        signals.post_command.connect(handler, sender=self.cmd.__class__)
        call_command(self.cmd, verbosity=0, interactive=False)
        handler.assert_called_once()
        args, kwargs = handler.call_args
        self.assertEqual(kwargs['instance'], self.cmd)
        self.assertEqual(kwargs['sender'], self.cmd.__class__)
