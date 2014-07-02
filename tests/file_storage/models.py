"""
42. Storing files according to a custom storage system

``FileField`` and its variations can take a ``storage`` argument to specify how
and where files should be stored.
"""

import os
import random
import tempfile

from django.db import models
from django.core.files.storage import FileSystemStorage


temp_storage_location = tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])
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
