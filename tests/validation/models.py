from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models


def validate_answer_to_universe(value):
    if value != 42:
        raise ValidationError('This is not the answer to life, universe and everything!', code='not42')


class ModelToValidate(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(default=datetime.now)
    number = models.IntegerField(db_column='number_val')
    parent = models.ForeignKey(
        'self',
        models.SET_NULL,
        blank=True, null=True,
        limit_choices_to={'number': 10},
    )
    email = models.EmailField(blank=True)
    ufm = models.ForeignKey(
        'UniqueFieldsModel',
        models.SET_NULL,
        to_field='unique_charfield',
        blank=True, null=True,
    )
    url = models.URLField(blank=True)
    f_with_custom_validator = models.IntegerField(blank=True, null=True, validators=[validate_answer_to_universe])
    f_with_iterable_of_validators = models.IntegerField(blank=True, null=True,
                                                        validators=(validate_answer_to_universe,))
    slug = models.SlugField(blank=True)

    def clean(self):
        super().clean()
        if self.number == 11:
            raise ValidationError('Invalid number supplied!')


class UniqueFieldsModel(models.Model):
    unique_charfield = models.CharField(max_length=100, unique=True)
    unique_integerfield = models.IntegerField(unique=True)
    non_unique_field = models.IntegerField()


class CustomPKModel(models.Model):
    my_pk_field = models.CharField(max_length=100, primary_key=True)


class UniqueTogetherModel(models.Model):
    cfield = models.CharField(max_length=100)
    ifield = models.IntegerField()
    efield = models.EmailField()

    class Meta:
        unique_together = (('ifield', 'cfield',), ['ifield', 'efield'])


class UniqueForDateModel(models.Model):
    start_date = models.DateField()
    end_date = models.DateTimeField()
    count = models.IntegerField(unique_for_date="start_date", unique_for_year="end_date")
    order = models.IntegerField(unique_for_month="end_date")
    name = models.CharField(max_length=100)


class CustomMessagesModel(models.Model):
    other = models.IntegerField(blank=True, null=True)
    number = models.IntegerField(
        db_column='number_val',
        error_messages={'null': 'NULL', 'not42': 'AAARGH', 'not_equal': '%s != me'},
        validators=[validate_answer_to_universe]
    )


class Author(models.Model):
    name = models.CharField(max_length=100)


class Article(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, models.CASCADE)
    pub_date = models.DateTimeField(blank=True)

    def clean(self):
        if self.pub_date is None:
            self.pub_date = datetime.now()


class Post(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField()

    def __str__(self):
        return self.name


class FlexibleDatePost(models.Model):
    title = models.CharField(max_length=50, unique_for_date='posted', blank=True)
    slug = models.CharField(max_length=50, unique_for_year='posted', blank=True)
    subtitle = models.CharField(max_length=50, unique_for_month='posted', blank=True)
    posted = models.DateField(blank=True, null=True)


class UniqueErrorsModel(models.Model):
    name = models.CharField(max_length=100, unique=True, error_messages={'unique': 'Custom unique name message.'})
    no = models.IntegerField(unique=True, error_messages={'unique': 'Custom unique number message.'})


class GenericIPAddressTestModel(models.Model):
    generic_ip = models.GenericIPAddressField(blank=True, null=True, unique=True)
    v4_ip = models.GenericIPAddressField(blank=True, null=True, protocol="ipv4")
    v6_ip = models.GenericIPAddressField(blank=True, null=True, protocol="ipv6")
    ip_verbose_name = models.GenericIPAddressField("IP Address Verbose", blank=True, null=True)


class GenericIPAddrUnpackUniqueTest(models.Model):
    generic_v4unpack_ip = models.GenericIPAddressField(null=True, blank=True, unique=True, unpack_ipv4=True)


# A model can't have multiple AutoFields
# Refs #12467.
assertion_error = None
try:
    class MultipleAutoFields(models.Model):
        auto1 = models.AutoField(primary_key=True)
        auto2 = models.AutoField(primary_key=True)
except AssertionError as exc:
    assertion_error = exc
assert str(assertion_error) == (
    "Model validation.MultipleAutoFields can't have more than one "
    "auto-generated field."
)
