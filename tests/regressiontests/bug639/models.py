import tempfile

from django.db import models
from django.core.files.storage import FileSystemStorage

temp_storage = FileSystemStorage(tempfile.gettempdir())

class Photo(models.Model):
    title = models.CharField(max_length=30)
    image = models.FileField(storage=temp_storage, upload_to='tests')
    
    # Support code for the tests; this keeps track of how many times save() gets
    # called on each instance.
    def __init__(self, *args, **kwargs):
        super(Photo, self).__init__(*args, **kwargs)
        self._savecount = 0
    
    def save(self):
        super(Photo, self).save()
        self._savecount += 1
