"""
Storing files according to a custom storage system

``FileField`` and its variations can take a ``storage`` argument to specify how
and where files should be stored.
"""

import random
import tempfile

from django.core.files.storage import FileSystemStorage
from django.db import models


class OldStyleFSStorage(FileSystemStorage):
    """
    Storage backend without support for the ``max_length`` argument in
    ``get_available_name()`` and ``save()``; for backward-compatibility and
    deprecation testing.
    """
    def get_available_name(self, name):
        return name

    def save(self, name, content):
        return super(OldStyleFSStorage, self).save(name, content)


temp_storage_location = tempfile.mkdtemp()
temp_storage = FileSystemStorage(location=temp_storage_location)


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
    old_style = models.FileField(
        storage=OldStyleFSStorage(location=temp_storage_location),
        upload_to='tests',
    )
