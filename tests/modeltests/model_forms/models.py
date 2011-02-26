"""
XX. Generating HTML forms from models

This is mostly just a reworking of the ``form_for_model``/``form_for_instance``
tests to use ``ModelForm``. As such, the text may not make sense in all cases,
and the examples are probably a poor fit for the ``ModelForm`` syntax. In other
words, most of these tests should be rewritten.
"""

import os
import tempfile

from django.db import models
from django.core.files.storage import FileSystemStorage

temp_storage_dir = tempfile.mkdtemp()
temp_storage = FileSystemStorage(temp_storage_dir)

ARTICLE_STATUS = (
    (1, 'Draft'),
    (2, 'Pending'),
    (3, 'Live'),
)

ARTICLE_STATUS_CHAR = (
    ('d', 'Draft'),
    ('p', 'Pending'),
    ('l', 'Live'),
)

class Category(models.Model):
    name = models.CharField(max_length=20)
    slug = models.SlugField(max_length=20)
    url = models.CharField('The URL', max_length=40)

    def __unicode__(self):
        return self.name

class Writer(models.Model):
    name = models.CharField(max_length=50, help_text='Use both first and last names.')

    def __unicode__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(max_length=50)
    slug = models.SlugField()
    pub_date = models.DateField()
    created = models.DateField(editable=False)
    writer = models.ForeignKey(Writer)
    article = models.TextField()
    categories = models.ManyToManyField(Category, blank=True)
    status = models.PositiveIntegerField(choices=ARTICLE_STATUS, blank=True, null=True)

    def save(self):
        import datetime
        if not self.id:
            self.created = datetime.date.today()
        return super(Article, self).save()

    def __unicode__(self):
        return self.headline

class ImprovedArticle(models.Model):
    article = models.OneToOneField(Article)

class ImprovedArticleWithParentLink(models.Model):
    article = models.OneToOneField(Article, parent_link=True)

class BetterWriter(Writer):
    score = models.IntegerField()

class WriterProfile(models.Model):
    writer = models.OneToOneField(Writer, primary_key=True)
    age = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s is %s" % (self.writer, self.age)

from django.contrib.localflavor.us.models import PhoneNumberField
class PhoneNumber(models.Model):
    phone = PhoneNumberField()
    description = models.CharField(max_length=20)

    def __unicode__(self):
        return self.phone

class TextFile(models.Model):
    description = models.CharField(max_length=20)
    file = models.FileField(storage=temp_storage, upload_to='tests', max_length=15)

    def __unicode__(self):
        return self.description

try:
    # If PIL is available, try testing ImageFields. Checking for the existence
    # of Image is enough for CPython, but for PyPy, you need to check for the
    # underlying modules If PIL is not available, ImageField tests are omitted.
    # Try to import PIL in either of the two ways it can end up installed.
    try:
        from PIL import Image, _imaging
    except ImportError:
        import Image, _imaging

    test_images = True

    class ImageFile(models.Model):
        def custom_upload_path(self, filename):
            path = self.path or 'tests'
            return '%s/%s' % (path, filename)

        description = models.CharField(max_length=20)

        # Deliberately put the image field *after* the width/height fields to
        # trigger the bug in #10404 with width/height not getting assigned.
        width = models.IntegerField(editable=False)
        height = models.IntegerField(editable=False)
        image = models.ImageField(storage=temp_storage, upload_to=custom_upload_path,
                                  width_field='width', height_field='height')
        path = models.CharField(max_length=16, blank=True, default='')

        def __unicode__(self):
            return self.description

    class OptionalImageFile(models.Model):
        def custom_upload_path(self, filename):
            path = self.path or 'tests'
            return '%s/%s' % (path, filename)

        description = models.CharField(max_length=20)
        image = models.ImageField(storage=temp_storage, upload_to=custom_upload_path,
                                  width_field='width', height_field='height',
                                  blank=True, null=True)
        width = models.IntegerField(editable=False, null=True)
        height = models.IntegerField(editable=False, null=True)
        path = models.CharField(max_length=16, blank=True, default='')

        def __unicode__(self):
            return self.description
except ImportError:
    test_images = False

class CommaSeparatedInteger(models.Model):
    field = models.CommaSeparatedIntegerField(max_length=20)

    def __unicode__(self):
        return self.field

class Product(models.Model):
    slug = models.SlugField(unique=True)

    def __unicode__(self):
        return self.slug

class Price(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __unicode__(self):
        return u"%s for %s" % (self.quantity, self.price)

    class Meta:
        unique_together = (('price', 'quantity'),)

class ArticleStatus(models.Model):
    status = models.CharField(max_length=2, choices=ARTICLE_STATUS_CHAR, blank=True, null=True)

class Inventory(models.Model):
   barcode = models.PositiveIntegerField(unique=True)
   parent = models.ForeignKey('self', to_field='barcode', blank=True, null=True)
   name = models.CharField(blank=False, max_length=20)

   def __unicode__(self):
      return self.name

class Book(models.Model):
    title = models.CharField(max_length=40)
    author = models.ForeignKey(Writer, blank=True, null=True)
    special_id = models.IntegerField(blank=True, null=True, unique=True)

    class Meta:
        unique_together = ('title', 'author')

class BookXtra(models.Model):
    isbn = models.CharField(max_length=16, unique=True)
    suffix1 = models.IntegerField(blank=True, default=0)
    suffix2 = models.IntegerField(blank=True, default=0)

    class Meta:
        unique_together = (('suffix1', 'suffix2'))
        abstract = True

class DerivedBook(Book, BookXtra):
    pass

class ExplicitPK(models.Model):
    key = models.CharField(max_length=20, primary_key=True)
    desc = models.CharField(max_length=20, blank=True, unique=True)
    class Meta:
        unique_together = ('key', 'desc')

    def __unicode__(self):
        return self.key

class Post(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField()

    def __unicode__(self):
        return self.name

class DerivedPost(Post):
    pass

class BigInt(models.Model):
    biggie = models.BigIntegerField()

    def __unicode__(self):
        return unicode(self.biggie)

class MarkupField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20
        super(MarkupField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        # don't allow this field to be used in form (real use-case might be
        # that you know the markup will always be X, but it is among an app
        # that allows the user to say it could be something else)
        # regressed at r10062
        return None

class CustomFieldForExclusionModel(models.Model):
    name = models.CharField(max_length=10)
    markup = MarkupField()

class FlexibleDatePost(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField(blank=True, null=True)