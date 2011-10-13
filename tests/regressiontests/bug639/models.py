import tempfile

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.forms import ModelForm


temp_storage_dir = tempfile.mkdtemp()
temp_storage = FileSystemStorage(temp_storage_dir)

class Photo(models.Model):
    title = models.CharField(max_length=30)
    image = models.FileField(storage=temp_storage, upload_to='tests')

    # Support code for the tests; this keeps track of how many times save()
    # gets called on each instance.
    def __init__(self, *args, **kwargs):
        super(Photo, self).__init__(*args, **kwargs)
        self._savecount = 0

    def save(self, force_insert=False, force_update=False):
        super(Photo, self).save(force_insert, force_update)
        self._savecount += 1

class PhotoForm(ModelForm):
    class Meta:
        model = Photo
