# coding: utf-8
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Poet(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'formtools'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Poem(models.Model):
    poet = models.ForeignKey(Poet)
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'formtools'

    def __str__(self):
        return self.name
