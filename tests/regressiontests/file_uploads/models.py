import tempfile
import os
from django.db import models
from django.core.files.storage import FileSystemStorage

temp_storage = FileSystemStorage(tempfile.mkdtemp())
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')

class FileModel(models.Model):
    testfile = models.FileField(storage=temp_storage, upload_to='test_upload')
