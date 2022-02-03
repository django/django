import io

from django.core.management import call_command
from django.test import TestCase


class CoreCommandsNoOutputTests(TestCase):
    available_apps = ["empty_models"]

    def test_sqlflush_no_tables(self):
        out = io.StringIO()
        err = io.StringIO()
        call_command("sqlflush", stdout=out, stderr=err)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "No tables found.\n")

    def test_sqlsequencereset_no_sequences(self):
        out = io.StringIO()
        err = io.StringIO()
        call_command("sqlsequencereset", "empty_models", stdout=out, stderr=err)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "No sequences found.\n")
