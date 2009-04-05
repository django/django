import os
import tempfile
import shutil
from django.db import models
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile

# Test for correct behavior of width_field/height_field.
# Of course, we can't run this without PIL.

try:
    # Checking for the existence of Image is enough for CPython, but
    # for PyPy, you need to check for the underlying modules
    from PIL import Image, _imaging
except ImportError:
    Image = None

# If we have PIL, do these tests
if Image:
    temp_storage_dir = tempfile.mkdtemp()
    temp_storage = FileSystemStorage(temp_storage_dir)

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

# Bug #9786: Ensure '==' and '!=' work correctly.
>>> image_data = open(os.path.join(os.path.dirname(__file__), "test1.png"), 'rb').read()
>>> p1 = Person(name="Bob")
>>> p1.mugshot.save("mug", ContentFile(image_data))
>>> p2 = Person.objects.get(name="Joe")
>>> p.mugshot == p2.mugshot
True
>>> p.mugshot != p2.mugshot
False
>>> p.mugshot != p1.mugshot
True

Bug #9508: Similarly to the previous test, make sure hash() works as expected
(equal items must hash to the same value).
>>> hash(p.mugshot) == hash(p2.mugshot)
True

# Bug #8175: correctly delete files that have been removed off the file system.
>>> import os
>>> p2 = Person(name="Fred")
>>> p2.mugshot.save("shot", ContentFile(image_data))
>>> os.remove(p2.mugshot.path)
>>> p2.delete()

# Bug #8534: FileField.size should not leave the file open.
>>> p3 = Person(name="Joan")
>>> p3.mugshot.save("shot", ContentFile(image_data))

# Get a "clean" model instance
>>> p3 = Person.objects.get(name="Joan")

# It won't have an opened file. This is a bit brittle since it depends on the
# the internals of FieldFile, but there's no other way of telling if the
# file's been opened or not.
>>> hasattr(p3.mugshot, '_file')
False

# After asking for the size, the file should still be closed.
>>> _ = p3.mugshot.size
>>> hasattr(p3.mugshot, '_file')
False

>>> shutil.rmtree(temp_storage_dir)
"""}

