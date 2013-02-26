# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import datetime
import tempfile

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


temp_storage_location = tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])
temp_storage = FileSystemStorage(location=temp_storage_location)


class BoundaryModel(models.Model):
    positive_integer = models.PositiveIntegerField(null=True, blank=True)


callable_default_value = 0
def callable_default():
    global callable_default_value
    callable_default_value = callable_default_value + 1
    return callable_default_value


class Defaults(models.Model):
    name = models.CharField(max_length=255, default='class default value')
    def_date = models.DateField(default = datetime.date(1980, 1, 1))
    value = models.IntegerField(default=42)
    callable_default = models.IntegerField(default=callable_default)


class ChoiceModel(models.Model):
    """For ModelChoiceField and ModelMultipleChoiceField tests."""
    name = models.CharField(max_length=10)


@python_2_unicode_compatible
class ChoiceOptionModel(models.Model):
    """Destination for ChoiceFieldModel's ForeignKey.
    Can't reuse ChoiceModel because error_message tests require that it have no instances."""
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return 'ChoiceOption %d' % self.pk


class ChoiceFieldModel(models.Model):
    """Model with ForeignKey to another model, for testing ModelForm
    generation with ModelChoiceField."""
    choice = models.ForeignKey(ChoiceOptionModel, blank=False,
                               default=lambda: ChoiceOptionModel.objects.get(name='default'))
    choice_int = models.ForeignKey(ChoiceOptionModel, blank=False, related_name='choice_int',
                                   default=lambda: 1)

    multi_choice = models.ManyToManyField(ChoiceOptionModel, blank=False, related_name='multi_choice',
                                          default=lambda: ChoiceOptionModel.objects.filter(name='default'))
    multi_choice_int = models.ManyToManyField(ChoiceOptionModel, blank=False, related_name='multi_choice_int',
                                              default=lambda: [1])

class OptionalMultiChoiceModel(models.Model):
    multi_choice = models.ManyToManyField(ChoiceOptionModel, blank=False, related_name='not_relevant',
                                          default=lambda: ChoiceOptionModel.objects.filter(name='default'))
    multi_choice_optional = models.ManyToManyField(ChoiceOptionModel, blank=True, null=True,
                                                   related_name='not_relevant2')


class FileModel(models.Model):
    file = models.FileField(storage=temp_storage, upload_to='tests')


@python_2_unicode_compatible
class Group(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return '%s' % self.name


class Cheese(models.Model):
    name = models.CharField(max_length=100)


class Article(models.Model):
    content = models.TextField()
