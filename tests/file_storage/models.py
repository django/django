"""
Storing files according to a custom storage system

``FileField`` and its variations can take a ``storage`` argument to specify how
and where files should be stored.
"""

import os
import random
import tempfile

from django.db import models
from django.core.files.storage import FileSystemStorage
from django.utils.crypto import get_random_string


class OldStyleFSStorage(FileSystemStorage):
    """
    Storage backend without support for ``max_length`` argument in
    ``get_available_name()``.
    Used for backward-compatibility and deprecation testing.
    """
    def get_available_name(self, name):
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        while self.exists(name):
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, get_random_string(7), file_ext))
        return name


temp_storage_location = tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])
temp_storage = FileSystemStorage(location=temp_storage_location)
temp_old_style_storage = OldStyleFSStorage(location=temp_storage_location)


class Storage(models.Model):
    def custom_upload_to(self, filename):
        return 'foo'

    def random_upload_to(self, filename):
        # This returns a different result each time,
        # to make sure it only gets called once.
        return '%s/%s' % (random.randint(100, 999), filename)

    normal = models.FileField(storage=temp_storage, upload_to='tests')
    custom = models.FileField(storage=temp_storage, upload_to=custom_upload_to)
    random = models.FileField(storage=temp_storage, upload_to=random_upload_to)
    default = models.FileField(storage=temp_storage, upload_to='tests', default='tests/default.txt')
    empty = models.FileField(storage=temp_storage)
    limited_length = models.FileField(storage=temp_storage, upload_to='tests', max_length=20)
    extended_length = models.FileField(storage=temp_storage, upload_to='tests', max_length=300)
    old_style = models.FileField(storage=temp_old_style_storage, upload_to='tests')
