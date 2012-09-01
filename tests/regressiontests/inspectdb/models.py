from django.db import models


class People(models.Model):
    name = models.CharField(max_length=255)

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
