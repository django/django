import io

from django.core.management import call_command
from django.test import TestCase


class CoreCommandsNoOutputTests(TestCase):
    available_apps = ['empty_models']

    def test_sqlflush_no_tables(self):
        err = io.StringIO()
        call_command('sqlflush', stderr=err)
        self.assertEqual(err.getvalue(), 'No tables found.\n')

    def test_sqlsequencereset_no_sequences(self):
        err = io.StringIO()
        call_command('sqlsequencereset', 'empty_models', stderr=err)
        self.assertEqual(err.getvalue(), 'No sequences found.\n')
