from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import ComplexValidator
from django.db import models
from django.test import TestCase

def validate_answer_to_universe(value):
    if value != 42:
        raise ValidationError('This is not the answer to life, universe and everything!', code='not42')

class ValidateFieldNotEqualsOtherField(ComplexValidator):
    def __init__(self, other_field):
        self.other_field = other_field

    def __call__(self, value, all_values={}, obj=None):
        if value == self.get_value(self.other_field, all_values, obj):
            raise ValidationError("Must not equal to %r's value" % self.other_field, code='not_equal', params=(self.other_field,))

class ModelToValidate(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(default=datetime.now)
    number = models.IntegerField()
    parent = models.ForeignKey('self', blank=True, null=True)
    email = models.EmailField(blank=True)
    url = models.URLField(blank=True)
    f_with_custom_validator = models.IntegerField(blank=True, null=True, validators=[validate_answer_to_universe, ValidateFieldNotEqualsOtherField('number')])

    def validate(self):
        super(ModelToValidate, self).validate()
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
        unique_together = (('ifield', 'cfield',),('ifield', 'efield'), )

class UniqueForDateModel(models.Model):
    start_date = models.DateField()
    end_date = models.DateTimeField()
    count = models.IntegerField(unique_for_date="start_date", unique_for_year="end_date")
    order = models.IntegerField(unique_for_month="end_date")
    name = models.CharField(max_length=100)

class CustomMessagesModel(models.Model):
    other  = models.IntegerField(blank=True, null=True)
    number = models.IntegerField(
            error_messages={'null': 'NULL', 'not42': 'AAARGH', 'not_equal': '%s != me'},
            validators=[validate_answer_to_universe, ValidateFieldNotEqualsOtherField('other')]
        )





