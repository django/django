import tempfile
import os
from django.db import models

UPLOAD_ROOT = tempfile.mkdtemp()
UPLOAD_TO = os.path.join(UPLOAD_ROOT, 'test_upload')

class FileModel(models.Model):
    testfile = models.FileField(upload_to=UPLOAD_TO)
