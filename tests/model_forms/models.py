import datetime
import os
import tempfile
import uuid

from django.core import validators
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

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


class Person(models.Model):
    name = models.CharField(max_length=100)


class Category(models.Model):
    name = models.CharField(max_length=20)
    slug = models.SlugField(max_length=20)
    url = models.CharField('The URL', max_length=40)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Writer(models.Model):
    name = models.CharField(max_length=50, help_text='Use both first and last names.')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Article(models.Model):
    headline = models.CharField(max_length=50)
    slug = models.SlugField()
    pub_date = models.DateField()
    created = models.DateField(editable=False)
    writer = models.ForeignKey(Writer, models.CASCADE)
    article = models.TextField()
    categories = models.ManyToManyField(Category, blank=True)
    status = models.PositiveIntegerField(choices=ARTICLE_STATUS, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = datetime.date.today()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.headline


class ImprovedArticle(models.Model):
    article = models.OneToOneField(Article, models.CASCADE)


class ImprovedArticleWithParentLink(models.Model):
    article = models.OneToOneField(Article, models.CASCADE, parent_link=True)


class BetterWriter(Writer):
    score = models.IntegerField()


class Publication(models.Model):
    title = models.CharField(max_length=30)
    date_published = models.DateField()

    def __str__(self):
        return self.title


def default_mode():
    return 'di'


def default_category():
    return 3


class PublicationDefaults(models.Model):
    MODE_CHOICES = (('di', 'direct'), ('de', 'delayed'))
    CATEGORY_CHOICES = ((1, 'Games'), (2, 'Comics'), (3, 'Novel'))
    title = models.CharField(max_length=30)
    date_published = models.DateField(default=datetime.date.today)
    datetime_published = models.DateTimeField(default=datetime.datetime(2000, 1, 1))
    mode = models.CharField(max_length=2, choices=MODE_CHOICES, default=default_mode)
    category = models.IntegerField(choices=CATEGORY_CHOICES, default=default_category)
    active = models.BooleanField(default=True)
    file = models.FileField(default='default.txt')


class Author(models.Model):
    publication = models.OneToOneField(Publication, models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=255)


class Author1(models.Model):
    publication = models.OneToOneField(Publication, models.CASCADE, null=False)
    full_name = models.CharField(max_length=255)


class WriterProfile(models.Model):
    writer = models.OneToOneField(Writer, models.CASCADE, primary_key=True)
    age = models.PositiveIntegerField()

    def __str__(self):
        return "%s is %s" % (self.writer, self.age)


class Document(models.Model):
    myfile = models.FileField(upload_to='unused', blank=True)


class TextFile(models.Model):
    description = models.CharField(max_length=20)
    file = models.FileField(storage=temp_storage, upload_to='tests', max_length=15)

    def __str__(self):
        return self.description


class CustomFileField(models.FileField):
    def save_form_data(self, instance, data):
        been_here = getattr(self, 'been_saved', False)
        assert not been_here, "save_form_data called more than once"
        setattr(self, 'been_saved', True)


class CustomFF(models.Model):
    f = CustomFileField(upload_to='unused', blank=True)


class FilePathModel(models.Model):
    path = models.FilePathField(path=os.path.dirname(__file__), match='models.py', blank=True)


try:
    from PIL import Image  # NOQA: detect if Pillow is installed

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

        def __str__(self):
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

        def __str__(self):
            return self.description

    class NoExtensionImageFile(models.Model):
        def upload_to(self, filename):
            return 'tests/no_extension'

        description = models.CharField(max_length=20)
        image = models.ImageField(storage=temp_storage, upload_to=upload_to)

        def __str__(self):
            return self.description

except ImportError:
    test_images = False


class Homepage(models.Model):
    url = models.URLField()


class Product(models.Model):
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.slug


class Price(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return "%s for %s" % (self.quantity, self.price)

    class Meta:
        unique_together = (('price', 'quantity'),)


class Triple(models.Model):
    left = models.IntegerField()
    middle = models.IntegerField()
    right = models.IntegerField()

    class Meta:
        unique_together = (('left', 'middle'), ('middle', 'right'))


class ArticleStatus(models.Model):
    status = models.CharField(max_length=2, choices=ARTICLE_STATUS_CHAR, blank=True, null=True)


class Inventory(models.Model):
    barcode = models.PositiveIntegerField(unique=True)
    parent = models.ForeignKey('self', models.SET_NULL, to_field='barcode', blank=True, null=True)
    name = models.CharField(blank=False, max_length=20)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Book(models.Model):
    title = models.CharField(max_length=40)
    author = models.ForeignKey(Writer, models.SET_NULL, blank=True, null=True)
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

    def __str__(self):
        return self.key


class Post(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField()

    def __str__(self):
        return self.title


class DateTimePost(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateTimeField(editable=False)

    def __str__(self):
        return self.title


class DerivedPost(Post):
    pass


class BigInt(models.Model):
    biggie = models.BigIntegerField()

    def __str__(self):
        return str(self.biggie)


class MarkupField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20
        super().__init__(*args, **kwargs)

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


class Colour(models.Model):
    name = models.CharField(max_length=50)

    def __iter__(self):
        yield from range(5)

    def __str__(self):
        return self.name


class ColourfulItem(models.Model):
    name = models.CharField(max_length=50)
    colours = models.ManyToManyField(Colour)


class CustomErrorMessage(models.Model):
    name1 = models.CharField(
        max_length=50,
        validators=[validators.validate_slug],
        error_messages={'invalid': 'Model custom error message.'},
    )
    name2 = models.CharField(
        max_length=50,
        validators=[validators.validate_slug],
        error_messages={'invalid': 'Model custom error message.'},
    )

    def clean(self):
        if self.name1 == 'FORBIDDEN_VALUE':
            raise ValidationError({'name1': [ValidationError('Model.clean() error messages.')]})
        elif self.name1 == 'FORBIDDEN_VALUE2':
            raise ValidationError({'name1': 'Model.clean() error messages (simpler syntax).'})
        elif self.name1 == 'GLOBAL_ERROR':
            raise ValidationError("Global error message.")


def today_callable_dict():
    return {"last_action__gte": datetime.datetime.today()}


def today_callable_q():
    return models.Q(last_action__gte=datetime.datetime.today())


class Character(models.Model):
    username = models.CharField(max_length=100)
    last_action = models.DateTimeField()


class StumpJoke(models.Model):
    most_recently_fooled = models.ForeignKey(
        Character,
        models.CASCADE,
        limit_choices_to=today_callable_dict,
        related_name="+",
    )
    has_fooled_today = models.ManyToManyField(Character, limit_choices_to=today_callable_q, related_name="+")


# Model for #13776
class Student(models.Model):
    character = models.ForeignKey(Character, models.CASCADE)
    study = models.CharField(max_length=30)


# Model for #639
class Photo(models.Model):
    title = models.CharField(max_length=30)
    image = models.FileField(storage=temp_storage, upload_to='tests')

    # Support code for the tests; this keeps track of how many times save()
    # gets called on each instance.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._savecount = 0

    def save(self, force_insert=False, force_update=False):
        super().save(force_insert, force_update)
        self._savecount += 1


class UUIDPK(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30)


# Models for #24706
class StrictAssignmentFieldSpecific(models.Model):
    title = models.CharField(max_length=30)
    _should_error = False

    def __setattr__(self, key, value):
        if self._should_error is True:
            raise ValidationError(message={key: "Cannot set attribute"}, code='invalid')
        super().__setattr__(key, value)


class StrictAssignmentAll(models.Model):
    title = models.CharField(max_length=30)
    _should_error = False

    def __setattr__(self, key, value):
        if self._should_error is True:
            raise ValidationError(message="Cannot set attribute", code='invalid')
        super().__setattr__(key, value)


# A model with ForeignKey(blank=False, null=True)
class Award(models.Model):
    name = models.CharField(max_length=30)
    character = models.ForeignKey(Character, models.SET_NULL, blank=False, null=True)


class NullableUniqueCharFieldModel(models.Model):
    codename = models.CharField(max_length=50, blank=True, null=True, unique=True)
