import datetime
import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Country(models.Model):
    name = models.CharField(max_length=255)
    iso_two_letter = models.CharField(max_length=2)


class ProxyCountry(Country):
    class Meta:
        proxy = True


class ProxyProxyCountry(ProxyCountry):
    class Meta:
        proxy = True


class ProxyMultiCountry(ProxyCountry):
    pass


class ProxyMultiProxyCountry(ProxyMultiCountry):
    class Meta:
        proxy = True


class Place(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True


class Restaurant(Place):
    pass


class Pizzeria(Restaurant):
    pass


class State(models.Model):
    two_letter_code = models.CharField(max_length=2, primary_key=True)


class TwoFields(models.Model):
    f1 = models.IntegerField(unique=True)
    f2 = models.IntegerField(unique=True)


class NoFields(models.Model):
    pass


class NullableFields(models.Model):
    # Fields in db.backends.oracle.BulkInsertMapper
    big_int_filed = models.BigIntegerField(null=True, default=1)
    binary_field = models.BinaryField(null=True, default=b'data')
    date_field = models.DateField(null=True, default=timezone.now)
    datetime_field = models.DateTimeField(null=True, default=timezone.now)
    decimal_field = models.DecimalField(null=True, max_digits=2, decimal_places=1, default=Decimal('1.1'))
    duration_field = models.DurationField(null=True, default=datetime.timedelta(1))
    float_field = models.FloatField(null=True, default=3.2)
    integer_field = models.IntegerField(null=True, default=2)
    null_boolean_field = models.NullBooleanField(null=True, default=False)
    positive_integer_field = models.PositiveIntegerField(null=True, default=3)
    positive_small_integer_field = models.PositiveSmallIntegerField(null=True, default=4)
    small_integer_field = models.SmallIntegerField(null=True, default=5)
    time_field = models.TimeField(null=True, default=timezone.now)
    # Fields not required in BulkInsertMapper
    char_field = models.CharField(null=True, max_length=4, default='char')
    email_field = models.EmailField(null=True, default='user@example.com')
    duration_field = models.DurationField(null=True, default=datetime.timedelta(1))
    file_field = models.FileField(null=True, default='file.txt')
    file_path_field = models.FilePathField(path='/tmp', null=True, default='file.txt')
    generic_ip_address_field = models.GenericIPAddressField(null=True, default='127.0.0.1')
    image_field = models.ImageField(null=True, default='image.jpg')
    slug_field = models.SlugField(null=True, default='slug')
    text_field = models.TextField(null=True, default='text')
    url_field = models.URLField(null=True, default='/')
    uuid_field = models.UUIDField(null=True, default=uuid.uuid4)
