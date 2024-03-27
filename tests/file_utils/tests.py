from django.core.exceptions import SuspiciousFileOperation
from django.core.files.utils import validate_file_name
from django.test import SimpleTestCase


class ValidateFileNameMixin:
    """A set of test helpers for the methods doing file name validation."""

    def do_call(self, name):
        raise NotImplementedError()

    def test_dangerous_paths_file_name(self):
        candidates = [
            "/tmp/..",
            "\\tmp\\..",
            "/tmp/.",
            "\\tmp\\.",
            "..",
            ".",
            "",
        ]
        for name in candidates:
            expected = f"Could not derive file name from '{name}'"
            with self.subTest(name=name):
                with self.assertRaisesMessage(SuspiciousFileOperation, expected):
                    self.do_call(name)

    def test_dangerous_paths_dir_name(
        self, msg="Detected path traversal attempt in '{name}'"
    ):
        candidates = [
            "../path",
            "tmp/../path",
            "tmp\\..\\path",
            "..\\path",
            "/tmp/../path",
            "\\tmp\\..\\path",
            "/tmp/path",
            "\\tmp\\path",
        ]
        for name in candidates:
            expected = msg.format(name=name)
            with self.subTest(name=name):
                with self.assertRaisesMessage(SuspiciousFileOperation, expected):
                    self.do_call(name)


class ValidateFileNameAllowRelativePathTests(ValidateFileNameMixin, SimpleTestCase):

    def do_call(self, name):
        validate_file_name(name, allow_relative_path=True)


class ValidateFileNameDisallowRelativePathTests(ValidateFileNameMixin, SimpleTestCase):

    def do_call(self, name):
        validate_file_name(name, allow_relative_path=False)

    def test_dangerous_paths_dir_name(self):
        msg = "File name '{name}' includes path elements"
        super().test_dangerous_paths_dir_name(msg=msg)
