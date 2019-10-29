"""
Storing files according to a custom storage system

``FileField`` and its variations can take a ``storage`` argument to specify how
and where files should be stored.
"""

import random
import tempfile
from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.db import models


class CustomValidNameStorage(FileSystemStorage):
    def get_valid_name(self, name):
        # mark the name to show that this was called
        return name + '_valid'


temp_storage_location = tempfile.mkdtemp()
temp_storage = FileSystemStorage(location=temp_storage_location)


class Storage(models.Model):
    def custom_upload_to(self, filename):
        return 'foo'

    def random_upload_to(self, filename):
        # This returns a different result each time,
        # to make sure it only gets called once.
        return '%s/%s' % (random.randint(100, 999), filename)

    def pathlib_upload_to(self, filename):
        return Path('bar') / filename

    normal = models.FileField(storage=temp_storage, upload_to='tests')
    custom = models.FileField(storage=temp_storage, upload_to=custom_upload_to)
    pathlib_callable = models.FileField(storage=temp_storage, upload_to=pathlib_upload_to)
    pathlib_direct = models.FileField(storage=temp_storage, upload_to=Path('bar'))
    random = models.FileField(storage=temp_storage, upload_to=random_upload_to)
    custom_valid_name = models.FileField(
        storage=CustomValidNameStorage(location=temp_storage_location),
        upload_to=random_upload_to,
    )
    default = models.FileField(storage=temp_storage, upload_to='tests', default='tests/default.txt')
    empty = models.FileField(storage=temp_storage)
    limited_length = models.FileField(storage=temp_storage, upload_to='tests', max_length=20)
    extended_length = models.FileField(storage=temp_storage, upload_to='tests', max_length=300)
