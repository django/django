import os
import tempfile
from django.db import models
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile

temp_storage = FileSystemStorage(tempfile.gettempdir())

# Test for correct behavior of width_field/height_field.
# Of course, we can't run this without PIL.

try:
    # Checking for the existence of Image is enough for CPython, but
    # for PyPy, you need to check for the underlying modules
    import Image, _imaging
except ImportError:
    Image = None

# If we have PIL, do these tests
if Image:
    class Person(models.Model):
        name = models.CharField(max_length=50)
        mugshot = models.ImageField(storage=temp_storage, upload_to='tests', 
                                    height_field='mug_height', 
                                    width_field='mug_width')
        mug_height = models.PositiveSmallIntegerField()
        mug_width = models.PositiveSmallIntegerField()
        
    __test__ = {'API_TESTS': """

>>> image_data = open(os.path.join(os.path.dirname(__file__), "test.png"), 'rb').read()
>>> p = Person(name="Joe")
>>> p.mugshot.save("mug", ContentFile(image_data))
>>> p.mugshot.width
16
>>> p.mugshot.height
16
>>> p.mug_height
16
>>> p.mug_width
16

"""}
    