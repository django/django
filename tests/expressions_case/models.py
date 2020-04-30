from django.db import models

try:
    from PIL import Image
except ImportError:
    Image = None


class CaseTestModel(models.Model):
    integer = models.IntegerField()
    integer2 = models.IntegerField(null=True)
    string = models.CharField(max_length=100, default='')

    big_integer = models.BigIntegerField(null=True)
    binary = models.BinaryField(default=b'')
    boolean = models.BooleanField(default=False)
    date = models.DateField(null=True, db_column='date_field')
    date_time = models.DateTimeField(null=True)
    decimal = models.DecimalField(max_digits=2, decimal_places=1, null=True, db_column='decimal_field')
    duration = models.DurationField(null=True)
    email = models.EmailField(default='')
    file = models.FileField(null=True, db_column='file_field')
    file_path = models.FilePathField(null=True)
    float = models.FloatField(null=True, db_column='float_field')
    if Image:
        image = models.ImageField(null=True)
    generic_ip_address = models.GenericIPAddressField(null=True)
    null_boolean = models.BooleanField(null=True)
    null_boolean_old = models.NullBooleanField()
    positive_integer = models.PositiveIntegerField(null=True)
    positive_small_integer = models.PositiveSmallIntegerField(null=True)
    positive_big_integer = models.PositiveSmallIntegerField(null=True)
    slug = models.SlugField(default='')
    small_integer = models.SmallIntegerField(null=True)
    text = models.TextField(default='')
    time = models.TimeField(null=True, db_column='time_field')
    url = models.URLField(default='')
    uuid = models.UUIDField(null=True)
    fk = models.ForeignKey('self', models.CASCADE, null=True)


class O2OCaseTestModel(models.Model):
    o2o = models.OneToOneField(CaseTestModel, models.CASCADE, related_name='o2o_rel')
    integer = models.IntegerField()


class FKCaseTestModel(models.Model):
    fk = models.ForeignKey(CaseTestModel, models.CASCADE, related_name='fk_rel')
    integer = models.IntegerField()


class Client(models.Model):
    REGULAR = 'R'
    GOLD = 'G'
    PLATINUM = 'P'
    ACCOUNT_TYPE_CHOICES = (
        (REGULAR, 'Regular'),
        (GOLD, 'Gold'),
        (PLATINUM, 'Platinum'),
    )
    name = models.CharField(max_length=50)
    registered_on = models.DateField()
    account_type = models.CharField(
        max_length=1,
        choices=ACCOUNT_TYPE_CHOICES,
        default=REGULAR,
    )
