import os
import tempfile
import uuid

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.fields.files import ImageField, ImageFieldFile
from django.db.models.fields.related import (
    ForeignKey, ForeignObject, ManyToManyField, OneToOneField,
)
from django.utils import six

try:
    from PIL import Image
except ImportError:
    Image = None


class Foo(models.Model):
    a = models.CharField(max_length=10)
    d = models.DecimalField(max_digits=5, decimal_places=3)


def get_foo():
    return Foo.objects.get(id=1)


class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, default=get_foo, related_name=b'bars')


class Whiz(models.Model):
    CHOICES = (
        ('Group 1', (
            (1, 'First'),
            (2, 'Second'),
        )
        ),
        ('Group 2', (
            (3, 'Third'),
            (4, 'Fourth'),
        )
        ),
        (0, 'Other'),
    )
    c = models.IntegerField(choices=CHOICES, null=True)


class Counter(six.Iterator):
    def __init__(self):
        self.n = 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.n > 5:
            raise StopIteration
        else:
            self.n += 1
            return (self.n, 'val-' + str(self.n))


class WhizIter(models.Model):
    c = models.IntegerField(choices=Counter(), null=True)


class WhizIterEmpty(models.Model):
    c = models.CharField(choices=(x for x in []), blank=True, max_length=1)


class BigD(models.Model):
    d = models.DecimalField(max_digits=38, decimal_places=30)


class FloatModel(models.Model):
    size = models.FloatField()


class BigS(models.Model):
    s = models.SlugField(max_length=255)


class SmallIntegerModel(models.Model):
    value = models.SmallIntegerField()


class IntegerModel(models.Model):
    value = models.IntegerField()


class BigIntegerModel(models.Model):
    value = models.BigIntegerField()
    null_value = models.BigIntegerField(null=True, blank=True)


class PositiveSmallIntegerModel(models.Model):
    value = models.PositiveSmallIntegerField()


class PositiveIntegerModel(models.Model):
    value = models.PositiveIntegerField()


class Post(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()


class NullBooleanModel(models.Model):
    nbfield = models.NullBooleanField()


class BooleanModel(models.Model):
    bfield = models.BooleanField(default=None)
    string = models.CharField(max_length=10, default='abc')


class DateTimeModel(models.Model):
    d = models.DateField()
    dt = models.DateTimeField()
    t = models.TimeField()


class DurationModel(models.Model):
    field = models.DurationField()


class NullDurationModel(models.Model):
    field = models.DurationField(null=True)


class PrimaryKeyCharModel(models.Model):
    string = models.CharField(max_length=10, primary_key=True)


class FksToBooleans(models.Model):
    """Model with FKs to models with {Null,}BooleanField's, #15040"""
    bf = models.ForeignKey(BooleanModel)
    nbf = models.ForeignKey(NullBooleanModel)


class FkToChar(models.Model):
    """Model with FK to a model with a CharField primary key, #19299"""
    out = models.ForeignKey(PrimaryKeyCharModel)


class RenamedField(models.Model):
    modelname = models.IntegerField(name="fieldname", choices=((1, 'One'),))


class VerboseNameField(models.Model):
    id = models.AutoField("verbose pk", primary_key=True)
    field1 = models.BigIntegerField("verbose field1")
    field2 = models.BooleanField("verbose field2", default=False)
    field3 = models.CharField("verbose field3", max_length=10)
    field4 = models.CommaSeparatedIntegerField("verbose field4", max_length=99)
    field5 = models.DateField("verbose field5")
    field6 = models.DateTimeField("verbose field6")
    field7 = models.DecimalField("verbose field7", max_digits=6, decimal_places=1)
    field8 = models.EmailField("verbose field8")
    field9 = models.FileField("verbose field9", upload_to="unused")
    field10 = models.FilePathField("verbose field10")
    field11 = models.FloatField("verbose field11")
    # Don't want to depend on Pillow in this test
    # field_image = models.ImageField("verbose field")
    field12 = models.IntegerField("verbose field12")
    field13 = models.IPAddressField("verbose field13")
    field14 = models.GenericIPAddressField("verbose field14", protocol="ipv4")
    field15 = models.NullBooleanField("verbose field15")
    field16 = models.PositiveIntegerField("verbose field16")
    field17 = models.PositiveSmallIntegerField("verbose field17")
    field18 = models.SlugField("verbose field18")
    field19 = models.SmallIntegerField("verbose field19")
    field20 = models.TextField("verbose field20")
    field21 = models.TimeField("verbose field21")
    field22 = models.URLField("verbose field22")
    field23 = models.UUIDField("verbose field23")
    field24 = models.DurationField("verbose field24")


class GenericIPAddress(models.Model):
    ip = models.GenericIPAddressField(null=True, protocol='ipv4')


###############################################################################
# These models aren't used in any test, just here to ensure they validate
# successfully.

# See ticket #16570.
class DecimalLessThanOne(models.Model):
    d = models.DecimalField(max_digits=3, decimal_places=3)


# See ticket #18389.
class FieldClassAttributeModel(models.Model):
    field_class = models.CharField

###############################################################################


class DataModel(models.Model):
    short_data = models.BinaryField(max_length=10, default=b'\x08')
    data = models.BinaryField()

###############################################################################
# FileField


class Document(models.Model):
    myfile = models.FileField(upload_to='unused')

###############################################################################
# ImageField

# If Pillow available, do these tests.
if Image:
    class TestImageFieldFile(ImageFieldFile):
        """
        Custom Field File class that records whether or not the underlying file
        was opened.
        """
        def __init__(self, *args, **kwargs):
            self.was_opened = False
            super(TestImageFieldFile, self).__init__(*args, **kwargs)

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

    class AbsctractPersonWithHeight(models.Model):
        """
        Abstract model that defines an ImageField with only one dimension field
        to make sure the dimension update is correctly run on concrete subclass
        instance post-initialization.
        """
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height')
        mugshot_height = models.PositiveSmallIntegerField()

        class Meta:
            abstract = True

    class PersonWithHeight(AbsctractPersonWithHeight):
        """
        Concrete model that subclass an abctract one with only on dimension
        field.
        """
        name = models.CharField(max_length=50)

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


class AllFieldsModel(models.Model):
    big_integer = models.BigIntegerField()
    binary = models.BinaryField()
    boolean = models.BooleanField(default=False)
    char = models.CharField(max_length=10)
    csv = models.CommaSeparatedIntegerField(max_length=10)
    date = models.DateField()
    datetime = models.DateTimeField()
    decimal = models.DecimalField(decimal_places=2, max_digits=2)
    duration = models.DurationField()
    email = models.EmailField()
    file_path = models.FilePathField()
    floatf = models.FloatField()
    integer = models.IntegerField()
    ip_address = models.IPAddressField()
    generic_ip = models.GenericIPAddressField()
    null_boolean = models.NullBooleanField()
    positive_integer = models.PositiveIntegerField()
    positive_small_integer = models.PositiveSmallIntegerField()
    slug = models.SlugField()
    small_integer = models.SmallIntegerField()
    text = models.TextField()
    time = models.TimeField()
    url = models.URLField()
    uuid = models.UUIDField()

    fo = ForeignObject(
        'self',
        from_fields=['abstract_non_concrete_id'],
        to_fields=['id'],
        related_name='reverse'
    )
    fk = ForeignKey(
        'self',
        related_name='reverse2'
    )
    m2m = ManyToManyField('self')
    oto = OneToOneField('self')

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    gfk = GenericForeignKey()
    gr = GenericRelation(DataModel)


###############################################################################


class UUIDModel(models.Model):
    field = models.UUIDField()


class NullableUUIDModel(models.Model):
    field = models.UUIDField(blank=True, null=True)


class PrimaryKeyUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)


class RelatedToUUIDModel(models.Model):
    uuid_fk = models.ForeignKey('PrimaryKeyUUIDModel')


class UUIDChild(PrimaryKeyUUIDModel):
    pass


class UUIDGrandchild(UUIDChild):
    pass
