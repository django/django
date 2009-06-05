import os
import tempfile

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # Python 2.3 fallback

try:
    # Checking for the existence of Image is enough for CPython, but for PyPy,
    # you need to check for the underlying modules.
    from PIL import Image, _imaging
except ImportError:
    Image = None

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.fields.files import ImageFieldFile, ImageField


class Foo(models.Model):
    a = models.CharField(max_length=10)
    d = models.DecimalField(max_digits=5, decimal_places=3)

def get_foo():
    return Foo.objects.get(id=1)

class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, default=get_foo)

class Whiz(models.Model):
    CHOICES = (
        ('Group 1', (
                (1,'First'),
                (2,'Second'),
            )
        ),
        ('Group 2', (
                (3,'Third'),
                (4,'Fourth'),
            )
        ),
        (0,'Other'),
    )
    c = models.IntegerField(choices=CHOICES, null=True)

class BigD(models.Model):
    d = models.DecimalField(max_digits=38, decimal_places=30)

class BigS(models.Model):
    s = models.SlugField(max_length=255)


###############################################################################
# ImageField

# If PIL available, do these tests.
if Image:
    class TestImageFieldFile(ImageFieldFile):
        """
        Custom Field File class that records whether or not the underlying file
        was opened.
        """
        def __init__(self, *args, **kwargs):
            self.was_opened = False
            super(TestImageFieldFile, self).__init__(*args,**kwargs)
        def open(self):
            self.was_opened = True
            super(TestImageFieldFile, self).open()

    class TestImageField(ImageField):
        attr_class = TestImageFieldFile

    # Set up a temp directory for file storage.
    temp_storage_dir = tempfile.mkdtemp()
    temp_storage = FileSystemStorage(temp_storage_dir)
    temp_upload_to_dir = os.path.join(temp_storage.location, 'tests')

    class Person(models.Model):
        """
        Model that defines an ImageField with no dimension fields.
        """
        name = models.CharField(max_length=50)
        mugshot = TestImageField(storage=temp_storage, upload_to='tests')

    class PersonWithHeight(models.Model):
        """
        Model that defines an ImageField with only one dimension field.
        """
        name = models.CharField(max_length=50)
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height')
        mugshot_height = models.PositiveSmallIntegerField()

    class PersonWithHeightAndWidth(models.Model):
        """
        Model that defines height and width fields after the ImageField.
        """
        name = models.CharField(max_length=50)
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()

    class PersonDimensionsFirst(models.Model):
        """
        Model that defines height and width fields before the ImageField.
        """
        name = models.CharField(max_length=50)
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')

    class PersonTwoImages(models.Model):
        """
        Model that:
        * Defines two ImageFields
        * Defines the height/width fields before the ImageFields
        * Has a nullalble ImageField
        """
        name = models.CharField(max_length=50)
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')
        headshot_height = models.PositiveSmallIntegerField(
                blank=True, null=True)
        headshot_width = models.PositiveSmallIntegerField(
                blank=True, null=True)
        headshot = TestImageField(blank=True, null=True,
                                  storage=temp_storage, upload_to='tests',
                                  height_field='headshot_height',
                                  width_field='headshot_width')

###############################################################################
