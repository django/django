from file_utils.tests import ValidateFileNameMixin

from django.core.files.storage import Storage
from django.test import SimpleTestCase


class CustomStorage(Storage):
    """Trivial but custom Storage subclass overriding the _save method."""

    def __init__(self, *args, name_after_save=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._name_after_save = name_after_save

    def _save(self, name, content):
        """Change `name` in a way that an invalid new name is returned.

        This mimics potential custom storages that do unexpected things in the
        _save method, receiving a valid and safe input name, but returning an
        invalid/unsafe name.

        """
        return self._name_after_save if self._name_after_save is not None else name

    def exists(self, name):
        return False


class StorageGenerateFilenameTests(ValidateFileNameMixin, SimpleTestCase):

    def do_call(self, name):
        return CustomStorage().generate_filename(name)


class StorageSaveTests(ValidateFileNameMixin, SimpleTestCase):

    def do_call(self, name):
        safe_name = "file-name.txt"
        s = CustomStorage(name_after_save=name)
        # The initial name passed to `save` is valid and safe but the returned
        # name from `_save` is not.
        return s.save(safe_name, content="irrelevant")
