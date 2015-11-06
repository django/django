# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class People(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self')


class Message(models.Model):
    from_field = models.ForeignKey(People, db_column='from_id')


class PeopleData(models.Model):
    people_pk = models.ForeignKey(People, primary_key=True)
    ssn = models.CharField(max_length=11)


class PeopleMoreData(models.Model):
    people_unique = models.ForeignKey(People, unique=True)
    license = models.CharField(max_length=255)


class DigitsInColumnName(models.Model):
    all_digits = models.CharField(max_length=11, db_column='123')
    leading_digit = models.CharField(max_length=11, db_column='4extra')
    leading_digits = models.CharField(max_length=11, db_column='45extra')


class SpecialName(models.Model):
    field = models.IntegerField(db_column='field')
    # Underscores
    field_field_0 = models.IntegerField(db_column='Field_')
    field_field_1 = models.IntegerField(db_column='Field__')
    field_field_2 = models.IntegerField(db_column='__field')
    # Other chars
    prc_x = models.IntegerField(db_column='prc(%) x')
    non_ascii = models.IntegerField(db_column='tamaño')

    class Meta:
        db_table = "inspectdb_special.table name"


class ColumnTypes(models.Model):
    id = models.AutoField(primary_key=True)
    big_int_field = models.BigIntegerField()
    bool_field = models.BooleanField(default=False)
    null_bool_field = models.NullBooleanField()
    char_field = models.CharField(max_length=10)
    null_char_field = models.CharField(max_length=10, blank=True, null=True)
    comma_separated_int_field = models.CommaSeparatedIntegerField(max_length=99)
    date_field = models.DateField()
    date_time_field = models.DateTimeField()
    decimal_field = models.DecimalField(max_digits=6, decimal_places=1)
    email_field = models.EmailField()
    file_field = models.FileField(upload_to="unused")
    file_path_field = models.FilePathField()
    float_field = models.FloatField()
    int_field = models.IntegerField()
    ip_address_field = models.IPAddressField()
    gen_ip_adress_field = models.GenericIPAddressField(protocol="ipv4")
    pos_int_field = models.PositiveIntegerField()
    pos_small_int_field = models.PositiveSmallIntegerField()
    slug_field = models.SlugField()
    small_int_field = models.SmallIntegerField()
    text_field = models.TextField()
    time_field = models.TimeField()
    url_field = models.URLField()


class UniqueTogether(models.Model):
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=10)
    from_field = models.IntegerField(db_column='from')
    non_unique = models.IntegerField(db_column='non__unique_column')
    non_unique_0 = models.IntegerField(db_column='non_unique__column')

    class Meta:
        unique_together = [
            ('field1', 'field2'),
            ('from_field', 'field1'),
            ('non_unique', 'non_unique_0'),
        ]
