import tempfile
from django.db import models

class Photo(models.Model):
    title = models.CharField(maxlength=30)
    image = models.ImageField(upload_to=tempfile.gettempdir())
    
    # Support code for the tests; this keeps track of how many times save() gets
    # called on each instance.
    def __init__(self, *args, **kwargs):
       super(Photo, self).__init__(*args, **kwargs)
       self._savecount = 0
    
    def save(self):
        super(Photo, self).save()
        self._savecount +=1