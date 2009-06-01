from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

class ModelToValidate(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(default=datetime.now)
    number = models.IntegerField()

    def validate(self):
        super(ModelToValidate, self).validate()
        if self.number == 11:
            raise ValidationError('Invalid number supplied!')

