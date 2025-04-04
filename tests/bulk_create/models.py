import datetime
import uuid
from decimal import Decimal

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

try:
    from PIL import Image
except ImportError:
    Image = None


class Country(models.Model):
    name = models.CharField(max_length=255)
    iso_two_letter = models.CharField(max_length=2)
    description = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["iso_two_letter", "name"],
                name="country_name_iso_unique",
            ),
        ]


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
    name = models.CharField(max_length=15, null=True)


class FieldsWithDbColumns(models.Model):
    rank = models.IntegerField(unique=True, db_column="rAnK")
    name = models.CharField(max_length=15, null=True, db_column="oTheRNaMe")


class UpsertConflict(models.Model):
    number = models.IntegerField(unique=True)
    rank = models.IntegerField()
    name = models.CharField(max_length=15)


class NoFields(models.Model):
    pass


class SmallAutoFieldModel(models.Model):
    id = models.SmallAutoField(primary_key=True)


class BigAutoFieldModel(models.Model):
    id = models.BigAutoField(primary_key=True)


class NullableFields(models.Model):
    # Fields in db.backends.oracle.BulkInsertMapper
    big_int_filed = models.BigIntegerField(null=True, default=1)
    binary_field = models.BinaryField(null=True, default=b"data")
    date_field = models.DateField(null=True, default=timezone.now)
    datetime_field = models.DateTimeField(null=True, default=timezone.now)
    decimal_field = models.DecimalField(
        null=True, max_digits=2, decimal_places=1, default=Decimal("1.1")
    )
    duration_field = models.DurationField(null=True, default=datetime.timedelta(1))
    float_field = models.FloatField(null=True, default=3.2)
    integer_field = models.IntegerField(null=True, default=2)
    null_boolean_field = models.BooleanField(null=True, default=False)
    positive_big_integer_field = models.PositiveBigIntegerField(
        null=True, default=2**63 - 1
    )
    positive_integer_field = models.PositiveIntegerField(null=True, default=3)
    positive_small_integer_field = models.PositiveSmallIntegerField(
        null=True, default=4
    )
    small_integer_field = models.SmallIntegerField(null=True, default=5)
    time_field = models.TimeField(null=True, default=timezone.now)
    auto_field = models.ForeignKey(NoFields, on_delete=models.CASCADE, null=True)
    small_auto_field = models.ForeignKey(
        SmallAutoFieldModel, on_delete=models.CASCADE, null=True
    )
    big_auto_field = models.ForeignKey(
        BigAutoFieldModel, on_delete=models.CASCADE, null=True
    )
    # Fields not required in BulkInsertMapper
    char_field = models.CharField(null=True, max_length=4, default="char")
    email_field = models.EmailField(null=True, default="user@example.com")
    file_field = models.FileField(null=True, default="file.txt")
    file_path_field = models.FilePathField(path="/tmp", null=True, default="file.txt")
    generic_ip_address_field = models.GenericIPAddressField(
        null=True, default="127.0.0.1"
    )
    if Image:
        image_field = models.ImageField(null=True, default="image.jpg")
    slug_field = models.SlugField(null=True, default="slug")
    text_field = models.TextField(null=True, default="text")
    url_field = models.URLField(null=True, default="/")
    uuid_field = models.UUIDField(null=True, default=uuid.uuid4)


class RelatedModel(models.Model):
    name = models.CharField(max_length=15, null=True)
    country = models.OneToOneField(Country, models.CASCADE, primary_key=True)
    big_auto_fields = models.ManyToManyField(BigAutoFieldModel)


class DbDefaultModel(models.Model):
    name = models.CharField(max_length=10)
    created_at = models.DateTimeField(db_default=Now())
