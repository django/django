from pathlib import Path

from django.core.management.commands.makemessages import TranslatableFile
from django.test import SimpleTestCase


class TranslatableFileTests(SimpleTestCase):
    def test_repr(self):
        dirpath = Path("dir")
        file_name = "example"
        trans_file = TranslatableFile(dirpath / file_name, locale_dir=None)
        self.assertEqual(
            repr(trans_file),
            "<TranslatableFile: %s>" % (dirpath / file_name),
        )

    def test_eq(self):
        dirpath = Path("dir")
        file_name = "example"
        trans_file = TranslatableFile(dirpath / file_name, locale_dir=None)
        trans_file_eq = TranslatableFile(dirpath / file_name, locale_dir=None)
        trans_file_not_eq = TranslatableFile(Path("tmp") / file_name, locale_dir=None)
        self.assertEqual(trans_file, trans_file_eq)
        self.assertNotEqual(trans_file, trans_file_not_eq)
