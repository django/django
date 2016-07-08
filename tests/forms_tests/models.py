# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import itertools
import tempfile

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

callable_default_counter = itertools.count()


def callable_default():
    return next(callable_default_counter)


temp_storage = FileSystemStorage(location=tempfile.mkdtemp())


class BoundaryModel(models.Model):
    positive_integer = models.PositiveIntegerField(null=True, blank=True)


class Defaults(models.Model):
    name = models.CharField(max_length=255, default='class default value')
    def_date = models.DateField(default=datetime.date(1980, 1, 1))
    value = models.IntegerField(default=42)
    callable_default = models.IntegerField(default=callable_default)


class ChoiceModel(models.Model):
    """For ModelChoiceField and ModelMultipleChoiceField tests."""
    CHOICES = [
        ('', 'No Preference'),
        ('f', 'Foo'),
        ('b', 'Bar'),
    ]

    INTEGER_CHOICES = [
        (None, 'No Preference'),
        (1, 'Foo'),
        (2, 'Bar'),
    ]

    STRING_CHOICES_WITH_NONE = [
        (None, 'No Preference'),
        ('f', 'Foo'),
        ('b', 'Bar'),
    ]

    name = models.CharField(max_length=10)
    choice = models.CharField(max_length=2, blank=True, choices=CHOICES)
    choice_string_w_none = models.CharField(
        max_length=2, blank=True, null=True, choices=STRING_CHOICES_WITH_NONE)
    choice_integer = models.IntegerField(choices=INTEGER_CHOICES, blank=True,
                                         null=True)


@python_2_unicode_compatible
class ChoiceOptionModel(models.Model):
    """Destination for ChoiceFieldModel's ForeignKey.
    Can't reuse ChoiceModel because error_message tests require that it have no instances."""
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return 'ChoiceOption %d' % self.pk


def choice_default():
    return ChoiceOptionModel.objects.get_or_create(name='default')[0].pk


def choice_default_list():
    return [choice_default()]


def int_default():
    return 1


def int_list_default():
    return [1]


class ChoiceFieldModel(models.Model):
    """Model with ForeignKey to another model, for testing ModelForm
    generation with ModelChoiceField."""
    choice = models.ForeignKey(
        ChoiceOptionModel,
        models.CASCADE,
        blank=False,
        default=choice_default,
    )
    choice_int = models.ForeignKey(
        ChoiceOptionModel,
        models.CASCADE,
        blank=False,
        related_name='choice_int',
        default=int_default,
    )
    multi_choice = models.ManyToManyField(
        ChoiceOptionModel,
        blank=False,
        related_name='multi_choice',
        default=choice_default_list,
    )
    multi_choice_int = models.ManyToManyField(
        ChoiceOptionModel,
        blank=False,
        related_name='multi_choice_int',
        default=int_list_default,
    )


class OptionalMultiChoiceModel(models.Model):
    multi_choice = models.ManyToManyField(
        ChoiceOptionModel,
        blank=False,
        related_name='not_relevant',
        default=choice_default,
    )
    multi_choice_optional = models.ManyToManyField(
        ChoiceOptionModel,
        blank=True,
        related_name='not_relevant2',
    )


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
