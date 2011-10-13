import tempfile
import os

from django.core.files.storage import FileSystemStorage
from django.db import models


temp_storage = FileSystemStorage(tempfile.mkdtemp())
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')

class FileModel(models.Model):
    testfile = models.FileField(storage=temp_storage, upload_to='test_upload')
