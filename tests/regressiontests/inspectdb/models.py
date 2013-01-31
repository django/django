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

class SpecialColumnName(models.Model):
    field = models.IntegerField(db_column='field')
    # Underscores
    field_field_0 = models.IntegerField(db_column='Field_')
    field_field_1 = models.IntegerField(db_column='Field__')
    field_field_2 = models.IntegerField(db_column='__field')
    # Other chars
    prc_x = models.IntegerField(db_column='prc(%) x')

class ColumnTypes(models.Model):
    id = models.AutoField(primary_key=True)
    field1 = models.BigIntegerField()
    field2 = models.BooleanField()
    field3 = models.CharField(max_length=10)
    field4 = models.CommaSeparatedIntegerField(max_length=99)
    field5 = models.DateField()
    field6 = models.DateTimeField()
    field7 = models.DecimalField(max_digits=6, decimal_places=1)
    field8 = models.EmailField()
    field9 = models.FileField(upload_to="unused")
    field10 = models.FilePathField()
    field11 = models.FloatField()
    field12 = models.IntegerField()
    field13 = models.IPAddressField()
    field14 = models.GenericIPAddressField(protocol="ipv4")
    field15 = models.NullBooleanField()
    field16 = models.PositiveIntegerField()
    field17 = models.PositiveSmallIntegerField()
    field18 = models.SlugField()
    field19 = models.SmallIntegerField()
    field20 = models.TextField()
    field21 = models.TimeField()
    field22 = models.URLField()
