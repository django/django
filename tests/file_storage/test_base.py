import os
from unittest import mock

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import Storage
from django.test import SimpleTestCase


class CustomStorage(Storage):
    """Simple Storage subclass implementing the bare minimum for testing."""

    def exists(self, name):
        return False

    def _save(self, name):
        return name


class StorageValidateFileNameTests(SimpleTestCase):
    invalid_file_names = [
        os.path.join("path", "to", os.pardir, "test.file"),
        os.path.join(os.path.sep, "path", "to", "test.file"),
    ]
    error_msg = "Detected path traversal attempt in '%s'"

    def test_validate_before_get_available_name(self):
        s = CustomStorage()
        # The initial name passed to `save` is not valid nor safe, fail early.
        for name in self.invalid_file_names:
            with self.subTest(name=name):
                with mock.patch.object(
                    s, "get_available_name"
                ) as mock_get_available_name:
                    with mock.patch.object(s, "_save") as mock_internal_save:
                        with self.assertRaisesMessage(
                            SuspiciousFileOperation, self.error_msg % name
                        ):
                            s.save(name, content="irrelevant")
                self.assertEqual(mock_get_available_name.mock_calls, [])
                self.assertEqual(mock_internal_save.mock_calls, [])

    def test_validate_after_get_available_name(self):
        s = CustomStorage()
        # The initial name passed to `save` is valid and safe, but the returned
        # name from `get_available_name` is not.
        for name in self.invalid_file_names:
            with self.subTest(name=name):
                with mock.patch.object(s, "get_available_name", return_value=name):
                    with mock.patch.object(s, "_save") as mock_internal_save:
                        with self.assertRaisesMessage(
                            SuspiciousFileOperation, self.error_msg % name
                        ):
                            s.save("valid-file-name.txt", content="irrelevant")
                self.assertEqual(mock_internal_save.mock_calls, [])

    def test_validate_after_internal_save(self):
        s = CustomStorage()
        # The initial name passed to `save` is valid and safe, but the result
        # from `_save` is not (this is achieved by monkeypatching _save).
        for name in self.invalid_file_names:
            with self.subTest(name=name):
                with mock.patch.object(s, "_save", return_value=name):
                    with self.assertRaisesMessage(
                        SuspiciousFileOperation, self.error_msg % name
                    ):
                        s.save("valid-file-name.txt", content="irrelevant")
