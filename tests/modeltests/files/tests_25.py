from __future__ import with_statement

import tempfile

from django.core.files import File
from django.utils.unittest import TestCase


class FileObjTests(TestCase):
    def test_context_manager(self):
        orig_file = tempfile.TemporaryFile()
        base_file = File(orig_file)
        with base_file as f:
            self.assertIs(base_file, f)
            self.assertFalse(f.closed)
        self.assertTrue(f.closed)
        self.assertTrue(orig_file.closed)
